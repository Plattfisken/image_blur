using System.Diagnostics;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapPost("/", async (HttpRequest request) =>
{
    if(request.ContentLength < 1) {
        return Results.BadRequest("No image provided");
    }

    var temporaryFileName = Path.ChangeExtension(Path.GetRandomFileName(), "jpeg");
    var temporaryFile = File.Create(temporaryFileName);
    
    await request.Body.CopyToAsync(temporaryFile);
    temporaryFile.Position = 0;
    temporaryFile.Close();

    const string pythonPath = @"/usr/local/bin/python3";
    const string  pythonScript = "./object_detection.py";
    var pythonProcess = new Process();
    pythonProcess.StartInfo = new ProcessStartInfo(pythonPath)
    {
        RedirectStandardOutput = true,
        UseShellExecute = false,
        CreateNoWindow = true,
        ArgumentList = { pythonScript, temporaryFileName }
    };
    pythonProcess.Start();
    await pythonProcess.WaitForExitAsync();
    var output = await pythonProcess.StandardOutput.ReadToEndAsync();
    var lines = output.Split('\n', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
    var resultFiles = lines.Where(l => l.EndsWith(".jpeg"));
    var resultFilePath = Path.Combine(Directory.GetCurrentDirectory(), resultFiles.First());
    
    
    const string mimeType = "image/jpeg";
    var result = Results.File(resultFilePath, contentType: mimeType);
    
    File.Delete(temporaryFileName);
    // TODO: Hur tar vi bort filen efter return?
    //File.Delete(resultFilePath);
    
    return result;
});

app.Run();