import discord

client = discord.Client()

async def copy_roles(source_guild, target_guild):
    role_map = {}
    for role in source_guild.roles:
        if role.is_default():
            role_map[role.id] = target_guild.default_role
            continue
        try:
            new_role = await target_guild.create_role(
                name=role.name,
                permissions=role.permissions,
                colour=role.colour,
                hoist=role.hoist,
                mentionable=role.mentionable,
                reason="Copy roles from source guild"
            )
            role_map[role.id] = new_role
            print(f'Role created: {role.name}')
        except Exception as e:
            print(f'Failed to create role {role.name}: {e}')
    return role_map

async def copy_categories(source_guild, target_guild):
    category_map = {}
    for category in source_guild.categories:
        try:
            new_category = await target_guild.create_category(
                name=category.name,
                overwrites=category.overwrites,
                reason="Copy category from source guild"
            )
            category_map[category.id] = new_category
            print(f'Category created: {category.name}')
        except Exception as e:
            print(f'Failed to create category {category.name}: {e}')
    return category_map

async def copy_channels(source_guild, target_guild, role_map, category_map):
    for channel in source_guild.channels:
        try:
            overwrites = {}
            for target, perm in channel.overwrites.items():
                if isinstance(target, discord.Role):
                    if target.id in role_map:
                        overwrites[role_map[target.id]] = perm
                else:
                    overwrites[target] = perm

            category = category_map.get(channel.category_id) if channel.category_id else None

            if isinstance(channel, discord.TextChannel):
                await target_guild.create_text_channel(
                    name=channel.name,
                    overwrites=overwrites,
                    category=category,
                    topic=channel.topic,
                    slowmode_delay=channel.slowmode_delay,
                    nsfw=channel.nsfw,
                    reason="Copy text channel from source guild"
                )
                print(f'Text channel created: {channel.name}')

            elif isinstance(channel, discord.VoiceChannel):
                await target_guild.create_voice_channel(
                    name=channel.name,
                    overwrites=overwrites,
                    category=category,
                    bitrate=channel.bitrate,
                    user_limit=channel.user_limit,
                    reason="Copy voice channel from source guild"
                )
                print(f'Voice channel created: {channel.name}')
            
        except Exception as e:
            print(f'Failed to create channel {channel.name}: {e}')

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

    source_id = int(input("Enter source server ID: "))
    target_id = int(input("Enter target server ID: "))

    source_guild = client.get_guild(source_id)
    target_guild = client.get_guild(target_id)

    if not source_guild:
        print("Source server not found.")
        await client.close()
        return

    if not target_guild:
        print("Target server not found.")
        await client.close()
        return

    print("Copying roles...")
    role_map = await copy_roles(source_guild, target_guild)

    print("Copying categories...")
    category_map = await copy_categories(source_guild, target_guild)

    print("Copying channels...")
    await copy_channels(source_guild, target_guild, role_map, category_map)

    print("Done copying everything except server name and icon.")
    await client.close()

token = input("Enter your Discord token: ")
client.run(token)
