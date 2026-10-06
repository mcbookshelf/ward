package dev.mcbookshelf.ward.commands.assertions;

import java.util.Collection;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.commands.arguments.selector.EntitySelector;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.AABB;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.test.AssertResult;
import dev.mcbookshelf.ward.test.TestExecutor;

class EntityAssertion implements Assertion {
	@Override
	public void attach(
			LiteralArgumentBuilder<CommandSourceStack> root,
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandBuildContext context,
			Mode mode) {
		root.then(Commands.literal("entity")
				.then(Commands.argument("entities", EntityArgument.entities())
						.executes(ctx -> mode.check(ctx, attempt -> check(attempt, false)))
						.then(Commands.literal("inside")
								.executes(ctx -> mode.check(ctx, attempt -> check(attempt, true))))));
	}

	private static AssertResult check(CommandContext<CommandSourceStack> context, boolean inside) throws CommandSyntaxException {
		EntitySelector selector = context.getArgument("entities", EntitySelector.class);
		Collection<? extends Entity> entities = selector.findEntities(context.getSource());
		int count = inside ? countInside(entities) : entities.size();
		String type = inside ? "entity_inside" : "entity";

		return AssertResult.of(count, negated -> Messages.translatable(
				(negated ? "ward.assert.not_" : "ward.assert.") + type,
				Assertion.getRawArgument(context, "entities"), count));
	}

	private static int countInside(Collection<? extends Entity> entities) throws CommandSyntaxException {
		AABB bounds = TestExecutor.current().getBounds().inflate(1);
		return (int) entities.stream().filter(entity -> bounds.contains(entity.position())).count();
	}
}
