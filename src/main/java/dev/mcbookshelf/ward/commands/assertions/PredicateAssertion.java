package dev.mcbookshelf.ward.commands.assertions;

import java.util.Optional;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.ResourceOrIdArgument;
import net.minecraft.core.Holder;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.parameters.LootContextParamSets;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;
import net.minecraft.world.phys.Vec3;

import dev.mcbookshelf.ward.AssertResult;

class PredicateAssertion implements Assertion {
	@Override
	public void attach(LiteralArgumentBuilder<CommandSourceStack> root, Context context) {
		root.then(Commands.literal("predicate")
				.then(Commands.argument("predicate", ResourceOrIdArgument.lootPredicate(context.buildContext()))
						.executes(ctx -> run(ctx, context))));
	}

	private static int run(CommandContext<CommandSourceStack> context, Context assertion) throws CommandSyntaxException {
		ServerLevel level = context.getSource().getLevel();
		Entity entity = context.getSource().getEntity();
		Vec3 pos = context.getSource().getPosition();

		return assertion.apply(() -> {
			Holder<LootItemCondition> predicate = ResourceOrIdArgument.getLootPredicate(context, "predicate");
			LootParams lootParams = new LootParams.Builder(level).withOptionalParameter(LootContextParams.THIS_ENTITY, entity)
					.withParameter(LootContextParams.ORIGIN, pos).create(LootContextParamSets.COMMAND);
			LootContext lootContext = new LootContext.Builder(lootParams).create(Optional.empty());
			lootContext.pushVisitedElement(LootContext.createVisitedEntry(predicate.value()));

			return AssertResult.of(predicate.value().test(lootContext) ? 1 : 0, "predicate",
					predicate.getRegisteredName());
		});
	}
}
