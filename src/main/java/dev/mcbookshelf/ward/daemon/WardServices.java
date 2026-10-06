package dev.mcbookshelf.ward.daemon;

import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import com.mojang.authlib.GameProfile;
import com.mojang.authlib.services.ServicesKeySet;

import net.minecraft.server.Services;
import net.minecraft.server.players.NameAndId;
import net.minecraft.server.players.ProfileResolver;
import net.minecraft.server.players.UserNameToIdResolver;

final class WardServices {
	private WardServices() {
	}

	static Services offline() {
		return new Services(
				null,
				ServicesKeySet.EMPTY,
				null,
				new OfflineUserNameToIdResolver(),
				new OfflineProfileResolver());
	}

	private static final class OfflineProfileResolver implements ProfileResolver {
		@Override
		public Optional<GameProfile> fetchByName(String name) {
			return Optional.empty();
		}

		@Override
		public Optional<GameProfile> fetchById(UUID id) {
			return Optional.empty();
		}
	}

	private static final class OfflineUserNameToIdResolver implements UserNameToIdResolver {
		private final Map<UUID, NameAndId> byId = new HashMap<>();
		private final Map<String, NameAndId> byName = new HashMap<>();

		@Override
		public void add(NameAndId value) {
			byId.put(value.id(), value);
			byName.put(value.name().toLowerCase(Locale.ROOT), value);
		}

		@Override
		public Optional<NameAndId> get(UUID id) {
			return Optional.ofNullable(byId.get(id));
		}

		@Override
		public Optional<NameAndId> get(String name) {
			return Optional.ofNullable(byName.get(name.toLowerCase(Locale.ROOT))).or(() -> Optional.of(NameAndId.createOffline(name)));
		}

		@Override
		public void resolveOfflineUsers(boolean value) {
		}

		@Override
		public void save() {
		}
	}
}
