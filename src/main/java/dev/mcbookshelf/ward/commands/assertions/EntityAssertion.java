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

import dev.mcbookshelf.ward.AssertResult;
import dev.mcbookshelf.ward.TestExecutor;

class EntityAssertion implements Assertion {
	@Override
	public void attach(
			LiteralArgumentBuilder<CommandSourceStack> root,
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandBuildContext context,
			Mode mode) {
		root.then(Commands.literal("entity")
				.then(Commands.argument("entities", EntityArgument.entities())
						.executes(ctx -> run(ctx, mode, false))
						.then(Commands.literal("inside")
								.executes(ctx -> run(ctx, mode, true)))));
	}

	private static int run(CommandContext<CommandSourceStack> context, Mode mode, boolean inside) throws CommandSyntaxException {
		EntitySelector selector = context.getArgument("entities", EntitySelector.class);
		TestExecutor executor = TestExecutor.current();
		AABB bounds = executor.getBounds().inflate(1);

		return mode.check(() -> {
			Collection<? extends Entity> entities = selector.findEntities(context.getSource());
			int count = inside
					? (int) entities.stream().filter(e -> bounds.contains(e.position())).count()
					: entities.size();

			return AssertResult.of(count, "entity" + (inside ? "_inside" : ""),
					Assertion.getRawArgument(context, "entities"), count);
		});
	}
}
