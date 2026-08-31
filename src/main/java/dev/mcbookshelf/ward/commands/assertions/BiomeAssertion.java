package dev.mcbookshelf.ward.commands.assertions;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.ResourceOrTagArgument;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.Registries;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.biome.Biome;

import dev.mcbookshelf.ward.AssertResult;

class BiomeAssertion implements Assertion {
	@Override
	public void attach(LiteralArgumentBuilder<CommandSourceStack> root, Context assertion) {
		root.then(Commands.literal("biome").then(Commands.argument("pos", BlockPosArgument.blockPos())
				.then(Commands.argument("biome", ResourceOrTagArgument.resourceOrTag(assertion.buildContext(), Registries.BIOME))
						.executes(ctx -> run(ctx, assertion)))));
	}

	private static int run(CommandContext<CommandSourceStack> context, Context assertion) throws CommandSyntaxException {
		ServerLevel level = context.getSource().getLevel();

		return assertion.check(() -> {
			BlockPos pos = BlockPosArgument.getLoadedBlockPos(context, "pos");
			ResourceOrTagArgument.Result<Biome> expect = ResourceOrTagArgument.getResourceOrTag(context, "biome", Registries.BIOME);
			Holder<Biome> found = level.getBiome(pos);

			return AssertResult.of(expect.test(found) ? 1 : 0, "biome",
					expect.asPrintable(), pos.toShortString(), found.getRegisteredName());
		});
	}
}
