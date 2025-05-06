## Dokumentation
Detta är ett litet bibliotek för att interagera med [_image_blur_](https://github.com/Plattfisken/image_blur/tree/main/image_blur).

Du använder biblioteket genom att anropa de statiska metoderna i den statiska klassen ImageBlur. Ingenting annat behöver göras. Följande metoder finns.
## Metoder

### BlurImages
```
Task<string> BlurImages(
  HttpClient httpClient,
  string baseUrl,
  string applicationName,
  string applicationGuid,
  float blurThreshold,
  float highlightThreshold,
  FileData[] files)
```
Anropar [_/enqueue_](https://github.com/Plattfisken/image_blur/tree/main/image_blur#enqueue)-endpoint och returnerar en sträng som innehåller GUID:en som används för att sedan hämta ut resultatet.

### CheckResult
```
Task<ImageBlurResult?> CheckResult(
  HttpClient httpClient,
  string baseUrl,
  string applicationName,
  string applicationGuid,
  string requestGuid)
```
Anropar [_/result_](https://github.com/Plattfisken/image_blur/tree/main/image_blur#result)-endpoint och returnerar en ImageBlurResult om ärendet har hanterats, annars null.

### AwaitResult
```
Task<ImageBlurResult> AwaitResult(
  HttpClient httpClient,
  string baseUrl,
  string applicationName,
  string applicationGuid, string requestGuid,
  int timeoutSeconds = 60,
  int checkIntervalMs = 300)
```
Anropar [CheckResult](#CheckResult) Med ett millisekundersinterval av _checkIntervalMs_ tills resultatet inte är null, eller tills det att _timeoutSeconds_ har passerats.
