package dev.mcbookshelf.ward.commands.assertions;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.NbtPathArgument;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.commands.ArgProvider;
import net.minecraft.server.commands.data.DataAccessor;
import net.minecraft.server.commands.data.DataCommands;

import dev.mcbookshelf.ward.AssertResult;

class DataAssertion implements Assertion {
	@Override
	public void attach(LiteralArgumentBuilder<CommandSourceStack> root, Context context) {
		for (ArgProvider<DataAccessor> provider : DataCommands.SOURCE_PROVIDERS) {
			root.then(provider.wrap(Commands.literal("data"), p -> p
					.then(Commands.argument("path", NbtPathArgument.nbtPath())
							.executes(ctx -> run(ctx, context, provider)))));
		}
	}

	private static int run(CommandContext<CommandSourceStack> context, Context assertion, ArgProvider<DataAccessor> provider) throws CommandSyntaxException {
		return assertion.apply(() -> {
			NbtPathArgument.NbtPath path = NbtPathArgument.getPath(context, "path");
			DataAccessor accessor = provider.access(context);
			CompoundTag data = accessor.getData();

			return AssertResult.of(path.countMatching(data), "data", path.asString(), data.toString());
		});
	}
}
