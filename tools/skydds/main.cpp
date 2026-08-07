#include "Cli.h"

#include <skydds/Export.h>
#include <skydds/SlotTable.h>

#include <cstdio>

int main(int argc, const char** argv)
{
	skydds::Options options;
	int exitCode = 0;
	if (!skydds::parseCommandLine(options, exitCode, argc, argv))
		return exitCode;

	const skydds::Slot* slot = skydds::findSlot(options.slot.c_str());
	if (!slot)
	{
		std::fprintf(stderr, "skydds: unknown slot '%s' (slots: %s)\n", options.slot.c_str(),
			skydds::slotNames());
		return 2;
	}

	skydds::ExportRequest request;
	request.inputPath = options.in;
	request.outputPath = options.out;
	request.slot = slot;
	request.alphaMode = options.alphaMode;
	request.resizePow2 = options.resizePow2;
	request.dryRun = options.dryRun;
	request.threads = options.jobs;

	skydds::ExportResult result = skydds::exportTexture(request);
	if (!result.success)
	{
		std::fprintf(stderr, "skydds: %s\n", result.error.c_str());
		bool usageError = result.error.find("slot '") != std::string::npos;
		return usageError ? 2 : 1;
	}

	if (result.alphaScanned && result.nonOpaqueTexels > 0 &&
		options.alphaMode == skydds::AlphaMode::Auto)
	{
		std::fprintf(stderr,
			"skydds: note: alpha content detected (%u texels < 255, min %u): selecting %s;"
			" pass '--alpha-mode none' to force %s\n", result.nonOpaqueTexels, result.minAlpha,
			skydds::formatName(result.format), skydds::formatName(slot->format));
	}

	if (options.dryRun || options.verbose)
	{
		std::printf("in:     %s\n", options.in.c_str());
		std::printf("out:    %s\n", options.out.c_str());
		std::printf("slot:   %s\n", slot->name);
		std::printf("format: %s (%s)\n", skydds::formatName(result.format),
			slot->srgb ? "sRGB data, _UNORM tag" : "linear");
		std::printf("size:   %ux%u, %u mip levels\n", result.width, result.height,
			result.mipLevels);
	}
	if (!options.dryRun && options.verbose)
		std::printf("wrote %s\n", options.out.c_str());
	return 0;
}
