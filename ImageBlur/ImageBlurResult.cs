using System.Drawing;
using System.Globalization;
using System.IO.Compression;
using System.Text;

namespace ImageBlur;

public record ImageBlurResult : IDisposable
{
    internal ImageBlurResult(ZipArchive resultFile)
    {
        var resultImages = new List<FileData>();

        var highlightedImages = new List<HighlightedImage>();
        var imageDict = new Dictionary<string, FileData>();
        var coordsDict = new Dictionary<string, RectangleF[]>();

        var unhandledImages = new List<UnhandledImage>();
        foreach (var entry in resultFile.Entries)
            switch (entry.FullName.Split('/').First())
            {
                case "result":
                    if (!string.IsNullOrEmpty(entry.Name))
                        resultImages.Add(new FileData(BytesFromEntry(entry), entry.Name, InferContentType(entry.Name)));
                    break;
                case "highlighted_images_for_manual_review":
                    if (!string.IsNullOrEmpty(entry.Name))
                    {
                        var fileNameWithoutExtension = Path.GetFileNameWithoutExtension(entry.Name);
                        if (Path.GetExtension(entry.Name) == ".txt")
                        {
                            var fileAsString = Encoding.UTF8.GetString(BytesFromEntry(entry));
                            var lines = fileAsString.Split('\n');
                            var rects = new List<RectangleF>(lines.Length);
                            foreach (var line in lines)
                            {
                                var coordsAsString = line.Split(',');
                                var coords = coordsAsString.Select(x =>
                                    float.Parse(x, NumberStyles.Any, CultureInfo.InvariantCulture)).ToArray();
                                var x1 = coords[0];
                                var y1 = coords[1];
                                var x2 = coords[2];
                                var y2 = coords[3];
                                var width = x2 - x1;
                                var height = y2 - y1;
                                var rect = new RectangleF(x1, y1, width, height);
                                rects.Add(rect);
                            }

                            coordsDict.Add(fileNameWithoutExtension, rects.ToArray());
                        }
                        else
                        {
                            imageDict.Add(fileNameWithoutExtension,
                                new FileData(BytesFromEntry(entry), entry.Name, InferContentType(entry.Name)));
                        }

                        if (coordsDict.TryGetValue(fileNameWithoutExtension, out var rectangles) &&
                            imageDict.TryGetValue(fileNameWithoutExtension, out var fileData))
                        {
                            var highlightedImage = new HighlightedImage(fileData, rectangles);
                            highlightedImages.Add(highlightedImage);
                        }
                    }

                    break;
                case "unhandled_files_too_large":
                    if (!string.IsNullOrEmpty(entry.Name))
                        unhandledImages.Add(new UnhandledImage(
                            new FileData(BytesFromEntry(entry), entry.Name, InferContentType(entry.Name)),
                            ErrorType.TooLarge));
                    break;
                case "unhandled_files_invalid_format":
                    if (!string.IsNullOrEmpty(entry.Name))
                        unhandledImages.Add(new UnhandledImage(
                            new FileData(BytesFromEntry(entry), entry.Name, InferContentType(entry.Name)),
                            ErrorType.InvalidFormat));
                    break;
            }

        static byte[] BytesFromEntry(ZipArchiveEntry entry)
        {
            var buffer = new byte[entry.Length];
            using var stream = entry.Open();
            stream.ReadExactly(buffer, 0, buffer.Length);
            return buffer;
        }

        ResultFile = resultFile;
        ResultImages = resultImages.ToArray();
        HighlightedImages = highlightedImages.ToArray();
        UnhandledImages = unhandledImages.ToArray();
    }

    public ZipArchive ResultFile { get; }
    public FileData[] ResultImages { get; }
    public HighlightedImage[] HighlightedImages { get; }
    public UnhandledImage[] UnhandledImages { get; }

    public void Dispose()
    {
        ResultFile.Dispose();
    }

    // TODO: How do we deal with this? Best would be to avoid it altogether
    private static string? InferContentType(string fileName)
    {
        var extension = Path.GetExtension(fileName);

        switch (extension.ToLowerInvariant())
        {
            case ".jpg":
            case ".jpeg":
            case ".jfif":
            case ".pjpeg":
            case ".pjp":
                return "image/jpeg";
            case ".png":
                return "image/png";
            case ".avif":
                return "image/avif";
            case ".webp":
                return "image/webp";
            default:
                return null;
        }
    }
}