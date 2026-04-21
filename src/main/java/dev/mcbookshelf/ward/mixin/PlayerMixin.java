package dev.mcbookshelf.ward.mixin;

import dev.mcbookshelf.ward.dummy.Dummy;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(Player.class)
public abstract class PlayerMixin {

    /**
     * Make sure attacks are able to knockback dummies.
     */
    @Redirect(method = "causeExtraKnockback", at = @At(value = "FIELD", target = "Lnet/minecraft/world/entity/Entity;hurtMarked:Z", ordinal = 0))
    private boolean velocityModifiedAndNotDummy(Entity target) {
        return target.hurtMarked && !(target instanceof Dummy);
    }
}
