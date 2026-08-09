#include "Export.h"

#include "Dds.h"
#include "Encode.h"
#include "ImageRGBA.h"
#include "Mips.h"

#include <utility>
#include <vector>

namespace skydds
{

namespace
{

unsigned int nextPow2(unsigned int v)
{
	unsigned int result = 1;
	while (result < v)
		result <<= 1;
	return result;
}

ExportResult failure(std::string error, bool usageError = false)
{
	ExportResult result;
	result.error = std::move(error);
	result.usageError = usageError;
	return result;
}

} // namespace

ExportResult exportTexture(const ExportRequest& request)
{
	ImageRGBA image = loadImage(request.inputPath);
	if (!image.isValid())
		return failure("failed to load '" + request.inputPath + "'");

	bool alphaWeighted = alphaIsTransparency(request.alphaKind);
	if (request.resizePow2)
	{
		unsigned int width = nextPow2(image.width);
		unsigned int height = nextPow2(image.height);
		if (width != image.width || height != image.height)
		{
			image = resizeImage(image, width, height, request.srgb, alphaWeighted);
			if (!image.isValid())
				return failure("failed to resize image");
		}
	}

	ExportResult result;
	result.width = image.width;
	result.height = image.height;
	result.mipLevels = mipLevelCount(image.width, image.height);
	if (request.dryRun)
	{
		result.success = true;
		return result;
	}

	bool keepsAlpha = formatHasAlpha(request.format);
	alphaWeighted = alphaWeighted && keepsAlpha;
	std::vector<ImageRGBA> chain =
		buildMipChain(std::move(image), result.mipLevels, request.srgb, alphaWeighted);
	// Alpha cutout loses coverage on higher mip levels, so bias it to preserve
	if (request.alphaKind == AlphaKind::Test && keepsAlpha)
		preserveAlphaCoverage(chain, request.alphaRef);

	std::vector<EncodedLevel> levels;
	levels.reserve(chain.size());
	for (const ImageRGBA& mip : chain)
	{
		if (!mip.isValid())
			return failure("failed to generate mipmaps");
		EncodedLevel level;
		level.width = mip.width;
		level.height = mip.height;
		level.blocks = encodeImage(mip, request.format, request.srgb, request.threads);
		levels.push_back(std::move(level));
	}

	if (!writeDds(request.outputPath, request.format, levels))
		return failure("failed to write '" + request.outputPath + "'");

	result.success = true;
	return result;
}

} // namespace skydds
