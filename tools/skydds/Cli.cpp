#include "Cli.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace skydds
{

namespace
{

const char* usage =
	"Usage: skydds --in <file.png> --out <file.dds> --format <f> --colorspace <c>\n"
	"              --alpha <a> [options]\n"
	"\n"
	"Convert a source image to a Skyrim SE DDS (BC-compressed, full mip chain).\n"
	"\n"
	"Required:\n"
	"  --in <file>       Source image (PNG or anything stb_image loads).\n"
	"  --out <file>      Output DDS path.\n"
	"  --format <f>      bc1, bc1a (1-bit alpha), bc4 or bc7.\n"
	"  --colorspace <c>  srgb or linear, the DDS tag is always _UNORM.\n"
	"  --alpha <a>       none, standard (transparency) or encoded (packed data,\n"
	"                    e.g. a specularity mask).\n"
	"\n"
	"Options:\n"
	"  --game se         Target game (only 'se' is supported).\n"
	"  --jobs <N>        Encoder threads (default: all cores).\n"
	"  --resize pow2     Round non-power-of-two dimensions up to the next power of two.\n"
	"  --alpha-ref <x>   Accepted and ignored (reserved for alpha coverage preservation).\n"
	"  --dry-run         Print the resolved format/settings without writing.\n"
	"  --verbose         Print progress detail.\n"
	"  --help            Show this help.\n";

bool fail(int& outExit, const char* message, const char* detail = nullptr)
{
	if (detail)
		std::fprintf(stderr, "skydds: %s '%s'\n", message, detail);
	else
		std::fprintf(stderr, "skydds: %s\n", message);
	std::fprintf(stderr, "Run 'skydds --help' for usage.\n");
	outExit = 2;
	return false;
}

} // namespace

bool parseCommandLine(Options& options, int& outExit, int argc, const char** argv)
{
	auto value = [&](int& i) -> const char*
	{
		if (i + 1 >= argc)
			return nullptr;
		return argv[++i];
	};

	bool hasFormat = false;
	bool hasColorSpace = false;
	bool hasAlpha = false;

	for (int i = 1; i < argc; ++i)
	{
		const char* arg = argv[i];
		if (std::strcmp(arg, "--help") == 0 || std::strcmp(arg, "-h") == 0)
		{
			std::printf("%s", usage);
			outExit = 0;
			return false;
		}
		else if (std::strcmp(arg, "--in") == 0)
		{
			const char* v = value(i);
			if (!v)
				return fail(outExit, "--in requires a value");
			options.in = v;
		}
		else if (std::strcmp(arg, "--out") == 0)
		{
			const char* v = value(i);
			if (!v)
				return fail(outExit, "--out requires a value");
			options.out = v;
		}
		else if (std::strcmp(arg, "--game") == 0)
		{
			const char* v = value(i);
			if (!v)
				return fail(outExit, "--game requires a value");
			options.game = v;
		}
		else if (std::strcmp(arg, "--jobs") == 0)
		{
			const char* v = value(i);
			char* end = nullptr;
			long jobs = v ? std::strtol(v, &end, 10) : 0;
			if (!v || *end != '\0' || jobs < 1)
				return fail(outExit, "--jobs requires a positive integer");
			options.jobs = static_cast<unsigned int>(jobs);
		}
		else if (std::strcmp(arg, "--resize") == 0)
		{
			const char* v = value(i);
			if (!v || std::strcmp(v, "pow2") != 0)
				return fail(outExit, "--resize only supports 'pow2'");
			options.resizePow2 = true;
		}
		else if (std::strcmp(arg, "--format") == 0)
		{
			const char* v = value(i);
			if (!v)
				return fail(outExit, "--format requires a value");
			if (std::strcmp(v, "bc1") == 0)
				options.format = BlockFormat::BC1;
			else if (std::strcmp(v, "bc1a") == 0)
				options.format = BlockFormat::BC1a;
			else if (std::strcmp(v, "bc4") == 0)
				options.format = BlockFormat::BC4;
			else if (std::strcmp(v, "bc7") == 0)
				options.format = BlockFormat::BC7;
			else
				return fail(outExit, "--format must be bc1, bc1a, bc4 or bc7; got", v);
			hasFormat = true;
		}
		else if (std::strcmp(arg, "--colorspace") == 0)
		{
			const char* v = value(i);
			if (!v)
				return fail(outExit, "--colorspace requires a value");
			if (std::strcmp(v, "srgb") == 0)
				options.srgb = true;
			else if (std::strcmp(v, "linear") == 0)
				options.srgb = false;
			else
				return fail(outExit, "--colorspace must be srgb or linear; got", v);
			hasColorSpace = true;
		}
		else if (std::strcmp(arg, "--alpha") == 0)
		{
			const char* v = value(i);
			if (!v)
				return fail(outExit, "--alpha requires a value");
			if (std::strcmp(v, "none") == 0)
				options.alphaKind = AlphaKind::None;
			else if (std::strcmp(v, "standard") == 0)
				options.alphaKind = AlphaKind::Standard;
			else if (std::strcmp(v, "encoded") == 0)
				options.alphaKind = AlphaKind::Encoded;
			else
				return fail(outExit, "--alpha must be none, standard or encoded; got", v);
			hasAlpha = true;
		}
		else if (std::strcmp(arg, "--alpha-ref") == 0)
		{
			// for alpha coverage preservation later
			if (!value(i))
				return fail(outExit, "--alpha-ref requires a value");
		}
		else if (std::strcmp(arg, "--dry-run") == 0)
			options.dryRun = true;
		else if (std::strcmp(arg, "--verbose") == 0)
			options.verbose = true;
		else
			return fail(outExit, "unknown argument", arg);
	}

	if (options.in.empty())
		return fail(outExit, "--in is required");
	if (options.out.empty())
		return fail(outExit, "--out is required");
	if (!hasFormat)
		return fail(outExit, "--format is required");
	if (!hasColorSpace)
		return fail(outExit, "--colorspace is required");
	if (!hasAlpha)
		return fail(outExit, "--alpha is required");
	if (options.game != "se")
		return fail(outExit, "only '--game se' is supported; got", options.game.c_str());
	return true;
}

} // namespace skydds
