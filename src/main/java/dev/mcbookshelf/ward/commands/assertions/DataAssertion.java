package dev.mcbookshelf.ward.commands.assertions;

import java.util.List;
import java.util.Objects;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.NbtPathArgument;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.commands.ArgProvider;
import net.minecraft.server.commands.data.DataAccessor;
import net.minecraft.server.commands.data.DataCommands;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.test.AssertResult;

class DataAssertion implements Assertion {
	@Override
	public void attach(
			LiteralArgumentBuilder<CommandSourceStack> root,
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandBuildContext context,
			Mode mode) {
		for (ArgProvider<DataAccessor> provider : DataCommands.SOURCE_PROVIDERS) {
			root.then(provider.wrap(Commands.literal("data"), p -> p
					.then(Commands.argument("path", NbtPathArgument.nbtPath())
							.executes(ctx -> mode.check(ctx, attempt -> check(NbtPathArgument.getPath(attempt, "path"), provider.access(attempt).getData()))))));
		}
	}

	private static AssertResult check(NbtPathArgument.NbtPath path, Tag data) {
		return AssertResult.of(path.countMatching(data), negated -> negated
				? Messages.translatable("ward.assert.not_data", path.asString())
				: mismatch(path, data));
	}

	private static Component mismatch(NbtPathArgument.NbtPath path, Tag data) {
		String raw = path.asString();
		List<Tag> found = List.of(data);
		String reached = "";

		for (NbtPathArgument.Node node : path.nodes) {
			List<Tag> next = node.get(found);
			if (next.isEmpty()) return describe(raw, found, reached, node);
			found = next;
			reached = raw.substring(0, path.nodeToOriginalPosition.getInt(node));
		}

		return describe(raw, found, reached);
	}

	private static Component describe(String raw, List<Tag> found, String at) {
		String value = found.size() == 1 ? found.getFirst().toString() : found.toString();

		return at.isEmpty()
				? Messages.translatable("ward.assert.data", raw, value)
				: Messages.translatable("ward.assert.data_at", raw, value, at);
	}

	private static Component describe(String raw, List<Tag> found, String reached, NbtPathArgument.Node unmatched) {
		if (!(unmatched instanceof NbtPathArgument.MatchObjectNode filter)) return describe(raw, found, reached);

		List<Tag> filtered = found.stream()
				.map(tag -> tag instanceof CompoundTag compound ? compound.get(filter.name) : null)
				.filter(Objects::nonNull)
				.toList();

		return filtered.isEmpty()
				? describe(raw, found, reached)
				: describe(raw, filtered, reached.isEmpty() ? filter.name : reached + "." + filter.name);
	}
}
