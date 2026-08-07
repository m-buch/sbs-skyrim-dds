#include "Cli.h"

#include <skydds/Export.h>

#include <cstdio>

namespace
{

const char* alphaName(skydds::AlphaKind kind)
{
	switch (kind)
	{
		case skydds::AlphaKind::Encoded:
			return "encoded";
		case skydds::AlphaKind::Standard:
			return "standard";
		default:
			return "none";
	}
}

} // namespace

int main(int argc, const char** argv)
{
	skydds::Options options;
	int exitCode = 0;
	if (!skydds::parseCommandLine(options, exitCode, argc, argv))
		return exitCode;

	skydds::ExportRequest request;
	request.inputPath = options.in;
	request.outputPath = options.out;
	request.format = options.format;
	request.srgb = options.srgb;
	request.alphaKind = options.alphaKind;
	request.resizePow2 = options.resizePow2;
	request.dryRun = options.dryRun;
	request.threads = options.jobs;

	skydds::ExportResult result = skydds::exportTexture(request);
	if (!result.success)
	{
		std::fprintf(stderr, "skydds: %s\n", result.error.c_str());
		return result.usageError ? 2 : 1;
	}

	if (options.dryRun || options.verbose)
	{
		std::printf("in:     %s\n", options.in.c_str());
		std::printf("out:    %s\n", options.out.c_str());
		std::printf("format: %s (%s)\n", skydds::formatName(options.format),
			options.srgb ? "sRGB data, _UNORM tag" : "linear");
		std::printf("alpha:  %s\n", alphaName(options.alphaKind));
		std::printf("size:   %ux%u, %u mip levels\n", result.width, result.height,
			result.mipLevels);
	}
	if (!options.dryRun && options.verbose)
		std::printf("wrote %s\n", options.out.c_str());
	return 0;
}
