using System.Text;
// See https://aka.ms/new-console-template for more information
foreach(var arg in args) {
    Console.WriteLine($"arg: {arg}");
    SaveBytesToFile(Encoding.UTF8.GetBytes(arg));
}

static string SaveBytesToFile(byte[] bytes) {
    int numSuffix = 0;
    var files = Directory.GetFiles(".");
    foreach(var name in files) {
        if(name.Contains("temp")) ++numSuffix;
    }
    var fileName = $"temp{numSuffix}";
    var file = File.Open(fileName, FileMode.CreateNew);
    file.Write(bytes, 0, bytes.Length);
    file.Close();
    return fileName;
}
