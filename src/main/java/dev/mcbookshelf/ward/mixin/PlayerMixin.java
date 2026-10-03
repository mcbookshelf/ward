package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.ModifyExpressionValue;
import com.llamalad7.mixinextras.sugar.Local;
import org.objectweb.asm.Opcodes;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;

import dev.mcbookshelf.ward.dummy.Dummy;

@Mixin(Player.class)
public abstract class PlayerMixin {
	/**
	 * Vanilla leaves the knockback of a player to its client, and a dummy has none.
	 */
	@ModifyExpressionValue(method = "causeExtraKnockback", at = @At(value = "FIELD", target = "Lnet/minecraft/world/entity/Entity;syncVelocity:Z", opcode = Opcodes.GETFIELD))
	private boolean syncVelocityAndNotDummy(boolean syncVelocity, @Local(argsOnly = true) Entity target) {
		return syncVelocity && !(target instanceof Dummy);
	}
}
