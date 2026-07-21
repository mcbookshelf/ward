package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import org.objectweb.asm.Opcodes;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;

import dev.mcbookshelf.ward.dummy.Dummy;

@Mixin(Player.class)
public abstract class PlayerMixin {
	/**
	 * Makes attacks knock back dummies. For players, vanilla undoes the server-side knockback
	 * and lets the client apply it from a packet. A dummy has no client, so it would never move.
	 */
	@WrapOperation(method = "causeExtraKnockback", at = @At(value = "FIELD", target = "Lnet/minecraft/world/entity/Entity;syncVelocity:Z", opcode = Opcodes.GETFIELD))
	private boolean velocityModifiedAndNotDummy(Entity target, Operation<Boolean> original) {
		return original.call(target) && !(target instanceof Dummy);
	}
}
