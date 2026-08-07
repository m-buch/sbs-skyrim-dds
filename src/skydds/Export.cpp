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

ExportResult failure(std::string error)
{
	ExportResult result;
	result.error = std::move(error);
	return result;
}

} // namespace

ExportResult exportTexture(const ExportRequest& request)
{
	if (!request.slot)
		return failure("no slot given");
	const Slot& slot = *request.slot;
	if (!slot.supported)
		return failure(std::string("slot '") + slot.name + "' is not implemented yet");
	if (request.alphaMode != AlphaMode::Auto && !slot.hasAlphaVariants)
	{
		return failure(std::string("slot '") + slot.name + "' has a fixed format; the alpha"
			" mode only applies to slots with alpha variants");
	}

	ImageRGBA image = loadImage(request.inputPath);
	if (!image.isValid())
		return failure("failed to load '" + request.inputPath + "'");

	if (request.resizePow2)
	{
		unsigned int width = nextPow2(image.width);
		unsigned int height = nextPow2(image.height);
		if (width != image.width || height != image.height)
		{
			image = resizeImage(image, width, height, slot.srgb,
				slot.alphaKind == AlphaKind::Standard);
			if (!image.isValid())
				return failure("failed to resize image");
		}
	}

	ExportResult result;
	result.format = slot.format;
	switch (request.alphaMode)
	{
		case AlphaMode::None:
			break;
		case AlphaMode::Blend:
			result.format = slot.formatAlpha;
			break;
		case AlphaMode::Test:
			result.format = slot.formatAlphaTest;
			break;
		case AlphaMode::Auto:
			if (slot.hasAlphaVariants)
			{
				result.alphaScanned = true;
				for (std::size_t i = 3; i < image.pixels.size(); i += 4)
				{
					std::uint8_t alpha = image.pixels[i];
					if (alpha < 255)
					{
						++result.nonOpaqueTexels;
						if (alpha < result.minAlpha)
							result.minAlpha = alpha;
					}
				}
				if (result.nonOpaqueTexels > 0)
					result.format = slot.formatAlpha;
			}
			break;
	}

	result.width = image.width;
	result.height = image.height;
	result.mipLevels = mipLevelCount(image.width, image.height);
	if (request.dryRun)
	{
		result.success = true;
		return result;
	}

	bool alphaWeighted = slot.alphaKind == AlphaKind::Standard && formatHasAlpha(result.format);
	std::vector<ImageRGBA> chain =
		buildMipChain(std::move(image), result.mipLevels, slot.srgb, alphaWeighted);
	std::vector<EncodedLevel> levels;
	levels.reserve(chain.size());
	for (const ImageRGBA& mip : chain)
	{
		if (!mip.isValid())
			return failure("failed to generate mipmaps");
		EncodedLevel level;
		level.width = mip.width;
		level.height = mip.height;
		level.blocks = encodeImage(mip, result.format, slot.srgb, request.threads);
		levels.push_back(std::move(level));
	}

	if (!writeDds(request.outputPath, result.format, levels))
		return failure("failed to write '" + request.outputPath + "'");

	result.success = true;
	return result;
}

} // namespace skydds
