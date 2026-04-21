package dev.mcbookshelf.ward.accessor;

/**
 * Duck interface for accessing EntitySelector internals via mixin.
 * <p>
 * This interface is implemented by EntitySelectorMixin to expose
 * the private playerName field for dummy player name extraction.
 */
public interface EntitySelectorAccessor {
    /**
     * Returns the player name from the selector, or null if not a player-specific selector.
     */
    String ward$getPlayerName();
}
