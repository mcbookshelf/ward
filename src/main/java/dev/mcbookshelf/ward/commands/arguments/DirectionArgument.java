package dev.mcbookshelf.ward.commands.arguments;

import com.mojang.brigadier.StringReader;
import com.mojang.brigadier.arguments.ArgumentType;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.mojang.brigadier.suggestion.Suggestions;
import com.mojang.brigadier.suggestion.SuggestionsBuilder;
import net.minecraft.core.Direction;

import java.util.Objects;
import java.util.concurrent.CompletableFuture;

public class DirectionArgument implements ArgumentType<Direction> {

    public Direction parse(StringReader reader) throws CommandSyntaxException {
        try {
            return Objects.requireNonNull(Direction.byName(reader.readUnquotedString()));
        } catch (Exception e) {
            throw CommandSyntaxException.BUILT_IN_EXCEPTIONS.dispatcherUnknownArgument().createWithContext(reader);
        }
    }

    public <S> CompletableFuture<Suggestions> listSuggestions(CommandContext<S> context, SuggestionsBuilder builder) {
        Direction.stream().forEach(d -> builder.suggest(d.getName()));
        return builder.buildFuture();
    }
}
