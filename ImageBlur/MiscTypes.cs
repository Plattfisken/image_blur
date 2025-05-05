using System.Drawing;

namespace ImageBlur;

public readonly struct FileData(byte[] fileBytes, string name, string contentType)
{
    // TODO: should this really be a stream? Or byte array? Something else?
    public byte[] FileBytes { get; } = fileBytes;
    public string Name { get; } = name;
    public string ContentType { get; } = contentType;
}

public readonly struct HighlightedImage(FileData fileData, RectangleF[] highlightedRectangles)
{
    public FileData Image { get; } = fileData;
    public RectangleF[] HighlightedRectangles { get; } = highlightedRectangles;
}

public readonly struct UnhandledImage(FileData fileData, ErrorType errorType)
{
    public FileData Image { get; } = fileData;
    public ErrorType ErrorType { get; } = errorType;
}

public enum ErrorType
{
    TooLarge,
    InvalidFormat
}