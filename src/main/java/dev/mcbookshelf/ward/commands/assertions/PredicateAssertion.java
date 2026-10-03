package dev.mcbookshelf.ward.commands.assertions;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.ResourceOrIdArgument;
import net.minecraft.core.Holder;
import net.minecraft.server.commands.ExecuteCommand;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.test.AssertResult;

class PredicateAssertion implements Assertion {
	@Override
	public void attach(
			LiteralArgumentBuilder<CommandSourceStack> root,
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandBuildContext context,
			Mode mode) {
		root.then(Commands.literal("predicate")
				.then(Commands.argument("predicate", ResourceOrIdArgument.lootPredicate(context))
						.executes(ctx -> mode.check(ctx, PredicateAssertion::check))));
	}

	private static AssertResult check(CommandContext<CommandSourceStack> context) {
		Holder<LootItemCondition> predicate = ResourceOrIdArgument.getLootPredicate(context, "predicate");

		return AssertResult.of(ExecuteCommand.checkCustomPredicate(context.getSource(), predicate), negated -> Messages.translatable(
				negated ? "ward.assert.not_predicate" : "ward.assert.predicate",
				Assertion.getRawArgument(context, "predicate")));
	}
}
