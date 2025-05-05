using System.Drawing;
using System.Globalization;
using System.IO.Compression;
using System.Net.Http.Headers;
using System.Text;
using System.Web;

namespace ImageBlur;

public static class ImageBlur
{
    public static async Task<FileData> BlurRectanglesInImage(HttpClient httpClient, string baseUrl,
        string applicationName, string applicationGuid, RectangleF[] rectangles, FileData file)
    {
        var uriBuilder = new UriBuilder($"{baseUrl}/blur_rects_in_image");
        
        var query = HttpUtility.ParseQueryString(string.Empty);
        query["application_name"] = applicationName;
        query["application_guid"] = applicationGuid;
        
        uriBuilder.Query = query.ToString();
        
        using var dataContent = new MultipartFormDataContent();
        using var fileStream = new MemoryStream(file.FileBytes);
        
        var streamContent = new StreamContent(fileStream);
        streamContent.Headers.ContentType = new MediaTypeHeaderValue(file.ContentType);
        dataContent.Add(streamContent, name: "image_file", fileName: file.Name);
        StringBuilder sb = new();
        foreach (var rectangle in rectangles)
        {
            string 
                x1 = rectangle.X.ToString(CultureInfo.InvariantCulture), 
                y1 = rectangle.Y.ToString(CultureInfo.InvariantCulture),
                x2 = (rectangle.X + rectangle.Width).ToString(CultureInfo.InvariantCulture),
                y2 = (rectangle.Y + rectangle.Height).ToString(CultureInfo.InvariantCulture);
            
            var csv = string.Join(",", x1, y1, x2, y2);
            sb.AppendLine(csv);
        }
        var utf8EncodedStr = Encoding.UTF8.GetBytes(sb.ToString());
        using var stream = new MemoryStream(utf8EncodedStr);
        
        dataContent.Add(new StreamContent(stream), name: "rect_file", fileName: file.Name);
        
        var response = await httpClient.PostAsync(uriBuilder.Uri, dataContent);
        response.EnsureSuccessStatusCode();

        await using var responseStream = await response.Content.ReadAsStreamAsync();
        var buffer = new byte[response.Content.Headers.ContentLength ?? 0];
        await responseStream.ReadExactlyAsync(buffer, 0 , buffer.Length);
        
        return new FileData(buffer, file.Name, file.ContentType);
    }

    public static async Task<string> BlurImages(
        HttpClient httpClient, string baseUrl, string applicationName, string applicationGuid,
        float blurThreshold, float highlightThreshold, FileData[] files)
    {
        using var dataContent = new MultipartFormDataContent();
        foreach (var file in files)
        {
            var fileStream = new MemoryStream(file.FileBytes);
            var streamContent = new StreamContent(fileStream);

            streamContent.Headers.ContentType = new MediaTypeHeaderValue(file.ContentType);
            dataContent.Add(streamContent, name: "image_upload_files", fileName: file.Name);
        }

        var uriBuilder = new UriBuilder($"{baseUrl}/enqueue");
        var query = HttpUtility.ParseQueryString(string.Empty);
        query["application_name"] = applicationName;
        query["application_guid"] = applicationGuid;
        query["blur_threshold"] = blurThreshold.ToString(CultureInfo.InvariantCulture);
        query["highlight_threshold"] = highlightThreshold.ToString(CultureInfo.InvariantCulture);
        uriBuilder.Query = query.ToString();
        using var response = await httpClient.PostAsync(uriBuilder.Uri, dataContent);
        response.EnsureSuccessStatusCode();
        var result = await response.Content.ReadAsStringAsync();
        // remove surrounding quotation marks
        if (result.First() == '"' && result.Last() == '"')
        {
            result = result.Remove(0, 1);
            result = result.Remove(result.Length - 1);
        }

        return result;
    }

    public static async Task<ImageBlurResult?> CheckResult(HttpClient httpClient, string baseUrl, 
        string applicationName, string applicationGuid, string requestGuid)
    {
        var uriBuilder = new UriBuilder($"{baseUrl}/result");        
        var query = HttpUtility.ParseQueryString(string.Empty);
        query["application_name"] = applicationName;
        query["application_guid"] = applicationGuid;
        query["request_guid"] = requestGuid;
        uriBuilder.Query = query.ToString();
        using var response = await httpClient.GetAsync(uriBuilder.Uri);
        response.EnsureSuccessStatusCode();
        if(response.Content.Headers.ContentType?.MediaType == "application/x-zip-compressed")
        {
            var responseStream = await response.Content.ReadAsStreamAsync();
            var zipArchive = new ZipArchive(responseStream, ZipArchiveMode.Read);
            return new ImageBlurResult(zipArchive);
        }
        return null;
    }

    public static async Task<ImageBlurResult> AwaitResult(HttpClient httpClient, string baseUrl,
        string applicationName, string applicationGuid, string requestGuid,
        int timeoutSeconds = 60, int checkIntervalMs = 300)
    {
        var timeStarted = DateTime.UtcNow;
        while ((DateTime.UtcNow - timeStarted).TotalSeconds < timeoutSeconds)
        {
            var result = await CheckResult(
                httpClient, baseUrl, applicationName, applicationGuid, requestGuid);
            if (result is not null) return result;
            Thread.Sleep(checkIntervalMs);
        }
        throw new TimeoutException();
    }

    public static async Task<ImageBlurResult> BlurImagesAndAwaitResult(
        HttpClient httpClient, string baseUrl, string applicationName, string applicationGuid,
        float blurThreshold, float highlightThreshold, FileData[] files,
        int timeoutSeconds = 60, int checkIntervalMs = 300)
    {  
        var requestGuid = await BlurImages(
            httpClient, baseUrl, applicationName, applicationGuid,
            blurThreshold, highlightThreshold, files);
        var result = await AwaitResult(httpClient, baseUrl, applicationName, 
            applicationGuid, requestGuid, timeoutSeconds, checkIntervalMs);
        return result;
    }
}