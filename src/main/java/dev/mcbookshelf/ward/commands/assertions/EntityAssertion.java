package dev.mcbookshelf.ward.commands.assertions;

import java.util.Collection;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

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
	public void attach(LiteralArgumentBuilder<CommandSourceStack> root, Context context) {
		root.then(Commands.literal("entity")
				.then(Commands.argument("entities", EntityArgument.entities())
						.executes(ctx -> run(ctx, context, false))
						.then(Commands.literal("inside")
								.executes(ctx -> run(ctx, context, true)))));
	}

	private static int run(CommandContext<CommandSourceStack> context, Context assertion, boolean inside) throws CommandSyntaxException {
		EntitySelector selector = context.getArgument("entities", EntitySelector.class);
		TestExecutor executor = TestExecutor.current();
		AABB bounds = executor.getBounds().inflate(1);

		return assertion.apply(() -> {
			Collection<? extends Entity> entities = selector.findEntities(context.getSource());
			int count = inside
					? (int) entities.stream().filter(e -> bounds.contains(e.position())).count()
					: entities.size();

			return AssertResult.of(count, "entity" + (inside ? "_inside" : ""),
					Assertion.getRawArgument(context, "entities"), count);
		});
	}
}
