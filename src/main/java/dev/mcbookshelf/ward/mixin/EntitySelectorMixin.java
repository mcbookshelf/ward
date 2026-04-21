package dev.mcbookshelf.ward.mixin;

import dev.mcbookshelf.ward.accessor.EntitySelectorAccessor;
import net.minecraft.commands.arguments.selector.EntitySelector;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;

@Mixin(EntitySelector.class)
public abstract class EntitySelectorMixin implements EntitySelectorAccessor {

    @Shadow
    @Final
    private String playerName;

    @Override
    @Unique
    public String ward$getPlayerName() {
        return this.playerName;
    }
}
