using System.Globalization;
using System.IO.Compression;
using System.Net.Http.Headers;
using System.Web;
using Microsoft.AspNetCore.Components.Forms;

namespace blazor_example;

public static class ImageBlur
{
    public static async Task<string> BlurImages(
        HttpClient httpClient, string baseUrl, string applicationName, string applicationGuid,
        float blurThreshold, float highlightThreshold, IBrowserFile[] files)
    {
        using var dataContent = new MultipartFormDataContent();
        foreach (var file in files)
        {
            var stream = file.OpenReadStream(maxAllowedSize: 50 * 1024 * 1024);
            var streamContent = new StreamContent(stream);

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
        var response = await httpClient.PostAsync(uriBuilder.Uri, dataContent);
        response.EnsureSuccessStatusCode();
        var result = await response.Content.ReadAsStringAsync();
        // remove surrounding qoutation marks
        if (result.First() == '"' && result.Last() == '"')
        {
            result = result.Remove(0, 1);
            result = result.Remove(result.Length - 1);
        }

        return result;
    }
    
    public static async Task<ZipArchive?> CheckResult(HttpClient httpClient, string baseUrl, 
        string applicationName, string applicationGuid, string requestGuid)
    {
        var uriBuilder = new UriBuilder($"{baseUrl}/result");        
        var query = HttpUtility.ParseQueryString(string.Empty);
        query["application_name"] = applicationName;
        query["application_guid"] = applicationGuid;
        query["request_guid"] = requestGuid;
        uriBuilder.Query = query.ToString();
        var response = await httpClient.GetAsync(uriBuilder.Uri);
        response.EnsureSuccessStatusCode();
        if(response.Content.Headers.ContentType?.MediaType == "application/x-zip-compressed")
        {
            var responseStream = await response.Content.ReadAsStreamAsync();
            var zipArchive = new ZipArchive(responseStream, ZipArchiveMode.Read);
            return zipArchive;
        }
        return null;
    }

    public static async Task<ZipArchive> AwaitResult(HttpClient httpClient, string baseUrl,
        string applicationName, string applicationGuid, string requestGuid, int timeoutSeconds)
    {
        var timeStarted = DateTime.UtcNow;
        while ((DateTime.UtcNow - timeStarted).TotalSeconds < timeoutSeconds)
        {
            var result = await CheckResult(
                httpClient, baseUrl, applicationName, applicationGuid, requestGuid);
            if (result is not null) return result;
            Thread.Sleep(500);
        }
        throw new TimeoutException();
    }

    public static async Task<ZipArchive> BlurImagesAndAwaitResult(
        HttpClient httpClient, string baseUrl, string applicationName, string applicationGuid,
        float blurThreshold, float highlightThreshold, IBrowserFile[] files, int timeoutSeconds)
    {  
        var requestGuid = await BlurImages(
            httpClient, baseUrl, applicationName, applicationGuid,
            blurThreshold, highlightThreshold, files);
        var result = await AwaitResult(httpClient, baseUrl, applicationName, 
            applicationGuid, requestGuid, timeoutSeconds);
        return result;
    }
}