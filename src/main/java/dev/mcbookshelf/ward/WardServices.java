package dev.mcbookshelf.ward;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import com.mojang.authlib.GameProfile;
import com.mojang.authlib.GameProfileRepository;
import com.mojang.authlib.minecraft.SessionService;
import com.mojang.authlib.services.ServicesKeySet;

import net.minecraft.server.Services;
import net.minecraft.server.players.NameAndId;
import net.minecraft.server.players.ProfileResolver;
import net.minecraft.server.players.UserNameToIdResolver;

/**
 * Offline stand-ins for the account services a MinecraftServer requires. The test server never
 * talks to Mojang, so every profile resolves locally.
 */
final class WardServices {
	static final Services OFFLINE = new Services(
			(SessionService) null,
			ServicesKeySet.EMPTY,
			(GameProfileRepository) null,
			new OfflineUserNameToIdResolver(),
			new OfflineProfileResolver());

	private WardServices() {
	}

	private static final class OfflineProfileResolver implements ProfileResolver {
		public Optional<GameProfile> fetchByName(final String name) {
			return Optional.empty();
		}

		public Optional<GameProfile> fetchById(final UUID id) {
			return Optional.empty();
		}
	}

	private static final class OfflineUserNameToIdResolver implements UserNameToIdResolver {
		private final Map<UUID, NameAndId> byId = new HashMap<>();
		private final Map<String, NameAndId> byName = new HashMap<>();

		public void add(NameAndId value) {
			byId.put(value.id(), value);
			byName.put(value.name(), value);
		}

		public Optional<NameAndId> get(UUID id) {
			return Optional.ofNullable(byId.get(id));
		}

		public Optional<NameAndId> get(String name) {
			return Optional.ofNullable(byName.get(name)).or(() -> Optional.of(NameAndId.createOffline(name)));
		}

		public void resolveOfflineUsers(final boolean value) {
		}

		public void save() {
		}
	}
}
