# Dokumentation
Detta är ett litet bibliotek för att interagera med [_image_blur_](https://github.com/Plattfisken/image_blur/tree/main/image_blur).

Du använder biblioteket genom att anropa de statiska metoderna i den statiska klassen ImageBlur. Ingenting annat behöver göras.
## Metoder

### BlurImages
```c#
Task<string> BlurImages(
  HttpClient httpClient,
  string baseUrl,
  string applicationName,
  string applicationGuid,
  float blurThreshold,
  float highlightThreshold,
  FileData[] files)
```
Anropar [`/enqueue`](https://github.com/Plattfisken/image_blur/tree/main/image_blur#enqueue)-endpoint asynkront och returnerar en sträng som innehåller GUID:en som används för att sedan hämta ut resultatet.

### CheckResult
```c#
Task<ImageBlurResult?> CheckResult(
  HttpClient httpClient,
  string baseUrl,
  string applicationName,
  string applicationGuid,
  string requestGuid)
```
Anropar [`/result`](https://github.com/Plattfisken/image_blur/tree/main/image_blur#result)-endpoint asynkront och returnerar en [`ImageBlurResult`](#ImageBlurResult) om ärendet har hanterats, annars `null`.

### AwaitResult
```c#
Task<ImageBlurResult> AwaitResult(
  HttpClient httpClient,
  string baseUrl,
  string applicationName,
  string applicationGuid, string requestGuid,
  int timeoutSeconds = 60,
  int checkIntervalMs = 300)
```
Anropar [`CheckResult`](#CheckResult) asynkront, med ett millisekundersinterval av `checkIntervalMs` tills resultatet inte är null, eller tills det att `timeoutSeconds` har passerats. Returnerar en [`ImageBlurResult`](#ImageBlurResult)

### BlurImagesAndAwaitResult
```c#
Task<ImageBlurResult> BlurImagesAndAwaitResult(
  HttpClient httpClient,
  string baseUrl,
  string applicationName,
  string applicationGuid,
  float blurThreshold,
  float highlightThreshold,
  FileData[] files,
  int timeoutSeconds = 60,
  int checkIntervalMs = 300)
```
Anropar först [`BlurImages`](#BlurImages) asynkront, och sedan [`AwaitResult`](#AwaitResult) asynkront. Returnerar en [`ImageBlurResult`](#ImageBlurResult)

### BlurRectanglesInImage
```c#
Task<FileData> BlurRectanglesInImage(
  HttpClient httpClient,
  string baseUrl,
  string applicationName,
  string applicationGuid,
  RectangleF[] rectangles,
  FileData file)
```
Anropar [`/blur_rects_in_image`](https://github.com/Plattfisken/image_blur/tree/main/image_blur#blur_rects_in_image)-endpoint asynkront. Returnerar en [`FileData`](#FileData).

## Typer

### ImageBlurResult
```c#
public record ImageBlurResult : IDisposable
{
  public ZipArchive ResultFile { get; }
  public FileData[] ResultImages { get; }
  public HighlightedImage[] HighlightedImages { get; }
  public UnhandledImage[] UnhandledImages { get; }
}
```
Representerar ett resultat från ett ärende. `ResultFile` innehåller zipfilen. Konstruktorn packar däremot upp allt som zipfilen innehåller, det går därför bra att använda sig av resultatet utan att behöva bry sig om zipfilen. `ResultImages` innehåller alla bilder som har blivit hanterade. `HighlightedImages` innehåller de bilder som har markerats. `UnhandledImages`innehåller de filer som inte har hanterats. `IDisposable` implementeras, då en `ZipArchive` behöver göras av med.

### HighlightedImage
```c#
public readonly struct HighlightedImage(FileData fileData, RectangleF[] highlightedRectangles)
{
  public FileData Image { get; } = fileData;
  public RectangleF[] HighlightedRectangles { get; } = highlightedRectangles;
}
```
Representerar en bild som har blivit markerad, innehåller den markerade bilden tillsammans med en array av rektanglar som innehåller de koordinater som har markerats.

### UnhandledImage
```c#
public readonly struct UnhandledImage(FileData fileData, ErrorType errorType)
{
  public FileData Image { get; } = fileData;
  public ErrorType ErrorType { get; } = errorType;
}
```
Representerar en fil som inte hanterades av API:et. [`ErrorType`](#ErrorType) beskriver anledningen.

### FileData
```c#
public readonly struct FileData(byte[] fileBytes, string name, string contentType)
{
    public byte[] FileBytes { get; } = fileBytes;
    public string Name { get; } = name;
    public string ContentType { get; } = contentType;
}
```
Innehåller informationen som behövs om en specifik fil. `FileBytes`: filens råa data. `Name`: filens namn. `ContentType`: filens MIME-type ("image/jpeg", t.ex).

### ErrorType
```c#
public enum ErrorType
{
  TooLarge,
  InvalidFormat
}
```
Anledningen till att en fil inte hanterades av API:et.
