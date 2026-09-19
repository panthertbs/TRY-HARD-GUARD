"""
: ! Aegis !
    + Discord: itsfizys
    + Community: https://discord.gg/aerox (AeroX Development )
    + for any queries reach out Community or DM me.
"""

import discord
from discord import ui
from discord.ext import commands

from utilities import checks
from utilities import converters
from utilities import decorators


async def setup(bot):
    await bot.add_cog(GuildTag(bot))


def _simple(text: str) -> ui.LayoutView:
    """Single-line container response."""
    view = ui.LayoutView(timeout=None)
    container = ui.Container(accent_color=0xFFFFFF)
    container.add_item(ui.TextDisplay(text))
    view.add_item(container)
    return view


class GuildTag(commands.Cog):
    """
    Module for guild tag management system.
    """

    def __init__(self, bot):
        self.bot = bot

    async def get_guild_tag_config(self, guild_id: int):
        query = """
                SELECT enabled, channel_id, message, roles
                FROM guild_tags
                WHERE server_id = $1
                """
        record = await self.bot.cxn.fetchrow(query, guild_id)
        if record:
            return {
                'enabled': record['enabled'],
                'channel_id': record['channel_id'],
                'message': record['message'],
                'roles': record['roles'] or []
            }
        return None

    async def get_guild_tag_users(self, guild_id: int):
        query = """
                SELECT user_id, adopted_at
                FROM guild_tag_users
                WHERE server_id = $1
                ORDER BY adopted_at DESC
                """
        records = await self.bot.cxn.fetch(query, guild_id)
        return records

    @decorators.group(
        name="guildtag",
        aliases=["gt"],
        brief="Manage guild tag settings.",
        invoke_without_command=True,
        case_insensitive=True,
    )
    @checks.guild_only()
    @checks.cooldown()
    async def guildtag(self, ctx):
        """
        Usage: {0}guildtag <subcommand>
        Alias: {0}gt
        Output:
            Manage guild tag settings for your server.
        Subcommands:
            enable: Enable guild tag system
            disable: Disable guild tag system
            channel: Manage guild tag channel
            role: Manage guild tag reward roles
            message: Set the guild tag message
            config: Show current guild tag settings
            list: List all users with the guild tag
        Notes:
            When users set their server tag to match the guild tag,
            they will automatically receive the configured roles
            and a message in the designated channel.
        """
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.guildtag_config)

    @guildtag.command(
        name="enable",
        brief="Enable guild tag for the server."
    )
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    @checks.cooldown()
    async def guildtag_enable(self, ctx):
        """
        Usage: {0}guildtag enable
        Alias: {0}gt enable
        Permission: Manage Guild
        Output:
            Enables the guild tag system for this server.
        """
        query = """
                INSERT INTO guild_tags (server_id, enabled)
                VALUES ($1, TRUE)
                ON CONFLICT (server_id)
                DO UPDATE SET enabled = TRUE
                """
        await self.bot.cxn.execute(query, ctx.guild.id)
        await ctx.send(view=_simple("Successfully **enabled** the guild tag system."), allowed_mentions=discord.AllowedMentions.none())

    @guildtag.command(
        name="disable",
        brief="Disable guild tag for the server."
    )
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    @checks.cooldown()
    async def guildtag_disable(self, ctx):
        """
        Usage: {0}guildtag disable
        Alias: {0}gt disable
        Permission: Manage Guild
        Output:
            Disables the guild tag system for this server.
        """
        query = """
                UPDATE guild_tags
                SET enabled = FALSE
                WHERE server_id = $1
                """
        await self.bot.cxn.execute(query, ctx.guild.id)
        await ctx.send(view=_simple("Successfully **disabled** the guild tag system."), allowed_mentions=discord.AllowedMentions.none())

    @guildtag.group(
        name="channel",
        brief="Manage guild tag channel.",
        invoke_without_command=True,
        case_insensitive=True,
    )
    @checks.guild_only()
    @checks.cooldown()
    async def guildtag_channel(self, ctx):
        """
        Usage: {0}guildtag channel <set/remove>
        Alias: {0}gt channel
        Output:
            Manage the channel where guild tag messages are sent.
        """
        if ctx.invoked_subcommand is None:
            await ctx.usage("channel <set/remove>")

    @guildtag_channel.command(
        name="set",
        brief="Set the guild tag channel."
    )
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    @checks.cooldown()
    async def guildtag_channel_set(self, ctx, channel: discord.TextChannel):
        """
        Usage: {0}guildtag channel set <channel>
        Alias: {0}gt channel set
        Permission: Manage Guild
        Output:
            Sets the channel where guild tag messages will be sent.
        """
        query = """
                INSERT INTO guild_tags (server_id, channel_id)
                VALUES ($1, $2)
                ON CONFLICT (server_id)
                DO UPDATE SET channel_id = excluded.channel_id
                """
        await self.bot.cxn.execute(query, ctx.guild.id, channel.id)
        await ctx.send(view=_simple(f"Guild tag channel set to {channel.mention}."), allowed_mentions=discord.AllowedMentions.none())

    @guildtag_channel.command(
        name="remove",
        aliases=["delete", "clear"],
        brief="Remove the guild tag channel."
    )
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    @checks.cooldown()
    async def guildtag_channel_remove(self, ctx):
        """
        Usage: {0}guildtag channel remove
        Aliases: {0}gt channel remove, {0}gt channel delete, {0}gt channel clear
        Permission: Manage Guild
        Output:
            Removes the guild tag channel configuration.
        """
        query = """
                UPDATE guild_tags
                SET channel_id = NULL
                WHERE server_id = $1
                """
        await self.bot.cxn.execute(query, ctx.guild.id)
        await ctx.send(view=_simple("Guild tag channel removed."), allowed_mentions=discord.AllowedMentions.none())

    @guildtag.group(
        name="role",
        brief="Manage guild tag reward roles.",
        invoke_without_command=True,
        case_insensitive=True,
    )
    @checks.guild_only()
    @checks.cooldown()
    async def guildtag_role(self, ctx):
        """
        Usage: {0}guildtag role <add/remove/list>
        Alias: {0}gt role
        Output:
            Manage roles that are given to users who adopt the guild tag.
        """
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.guildtag_role_list)

    @guildtag_role.command(
        name="add",
        brief="Add a role as guild tag reward role."
    )
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    @checks.bot_has_perms(manage_roles=True)
    @checks.cooldown()
    async def guildtag_role_add(self, ctx, *, role: converters.DiscordRole):
        """
        Usage: {0}guildtag role add <role>
        Alias: {0}gt role add
        Permission: Manage Guild
        Output:
            Adds a role to the list of guild tag reward roles.
        """
        res = await checks.role_priv(ctx, role)
        if res:
            return await ctx.fail(res)

        query = "SELECT roles FROM guild_tags WHERE server_id = $1"
        record = await self.bot.cxn.fetchrow(query, ctx.guild.id)
        current_roles = record['roles'] if record and record['roles'] else []

        if role.id in current_roles:
            return await ctx.fail(f"Role {role.mention} is already a guild tag reward role.")

        current_roles.append(role.id)

        query = """
                INSERT INTO guild_tags (server_id, roles)
                VALUES ($1, $2)
                ON CONFLICT (server_id)
                DO UPDATE SET roles = excluded.roles
                """
        await self.bot.cxn.execute(query, ctx.guild.id, current_roles)
        await ctx.send(view=_simple(f"{role.mention} added as a guild tag reward role."), allowed_mentions=discord.AllowedMentions.none())

    @guildtag_role.command(
        name="remove",
        aliases=["delete", "rm"],
        brief="Remove a role from guild tag rewards."
    )
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    @checks.cooldown()
    async def guildtag_role_remove(self, ctx, *, role: converters.DiscordRole):
        """
        Usage: {0}guildtag role remove <role>
        Aliases: {0}gt role remove, {0}gt role delete, {0}gt role rm
        Permission: Manage Guild
        Output:
            Removes a role from the list of guild tag reward roles.
        """
        query = "SELECT roles FROM guild_tags WHERE server_id = $1"
        record = await self.bot.cxn.fetchrow(query, ctx.guild.id)

        if not record or not record['roles']:
            return await ctx.fail("No guild tag reward roles configured.")

        current_roles = record['roles']

        if role.id not in current_roles:
            return await ctx.fail(f"Role {role.mention} is not a guild tag reward role.")

        current_roles.remove(role.id)

        query = "UPDATE guild_tags SET roles = $1 WHERE server_id = $2"
        await self.bot.cxn.execute(query, current_roles, ctx.guild.id)
        await ctx.send(view=_simple(f"{role.mention} removed from guild tag reward roles."), allowed_mentions=discord.AllowedMentions.none())

    @guildtag_role.command(
        name="list",
        brief="List all guild tag reward roles."
    )
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    @checks.cooldown()
    async def guildtag_role_list(self, ctx):
        """
        Usage: {0}guildtag role list
        Alias: {0}gt role list
        Permission: Manage Guild
        Output:
            Lists all roles configured as guild tag rewards.
        """
        query = "SELECT roles FROM guild_tags WHERE server_id = $1"
        record = await self.bot.cxn.fetchrow(query, ctx.guild.id)

        if not record or not record['roles']:
            return await ctx.fail("No guild tag reward roles configured.")

        roles = [ctx.guild.get_role(rid).mention for rid in record['roles'] if ctx.guild.get_role(rid)]

        if not roles:
            return await ctx.fail("No valid guild tag reward roles found.")

        view = ui.LayoutView(timeout=None)
        container = ui.Container(accent_color=0xFFFFFF)
        container.add_item(ui.TextDisplay("## Reward Roles"))
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay("\n".join(roles)))
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay(f"-# Total: {len(roles)} role{'s' if len(roles) != 1 else ''}"))
        view.add_item(container)
        await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

    @guildtag.group(
        name="message",
        brief="Set the guild tag message.",
        invoke_without_command=True,
        case_insensitive=True,
    )
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    @checks.cooldown()
    async def guildtag_message(self, ctx, *, message: str = None):
        """
        Usage: {0}guildtag message <message>
        Alias: {0}gt message
        Permission: Manage Guild
        Output:
            Sets a plain text message sent when users adopt the guild tag.
        Notes:
            Available placeholders: {user.mention} {user.name} {user.id} {server.name}
        """
        if message is None:
            view = ui.LayoutView(timeout=None)
            container = ui.Container(accent_color=0xFFFFFF)
            container.add_item(ui.TextDisplay("## guildtag message"))
            container.add_item(ui.Separator())
            container.add_item(ui.TextDisplay(
                "Set a plain text message sent to the configured channel when a user adopts the guild tag.\n\n"
                "**Arguments**\n"
                f"- `message` — The message to send *(required)*\n\n"
                "**Subcommands**\n"
                f"- `{ctx.prefix}guildtag message variables` — View available placeholders\n"
                f"- `{ctx.prefix}guildtag message remove` — Remove the current message"
            ))
            view.add_item(container)
            await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())
            return

        query = """
                INSERT INTO guild_tags (server_id, message)
                VALUES ($1, $2)
                ON CONFLICT (server_id)
                DO UPDATE SET message = excluded.message
                """
        await self.bot.cxn.execute(query, ctx.guild.id, message)
        await ctx.send(view=_simple("Guild tag message updated."), allowed_mentions=discord.AllowedMentions.none())

    @guildtag_message.command(
        name="variables",
        aliases=["vars", "placeholders"],
        brief="Show available message variables."
    )
    @checks.guild_only()
    @checks.cooldown()
    async def guildtag_message_variables(self, ctx):
        """
        Usage: {0}guildtag message variables
        Aliases: {0}gt message vars, {0}gt message placeholders
        Output:
            Shows all variables available for use in the guild tag message.
        """
        view = ui.LayoutView(timeout=None)
        container = ui.Container(accent_color=0xFFFFFF)
        container.add_item(ui.TextDisplay("## Message Variables"))
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay(
            f"- `{{user.mention}}` — {ctx.author.mention}\n"
            f"- `{{user.name}}` — {ctx.author.name}\n"
            f"- `{{user.id}}` — {ctx.author.id}\n"
            f"- `{{server.name}}` — {ctx.guild.name}"
        ))
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay("-# Use these in your message to personalise the guild tag notification."))
        view.add_item(container)
        await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

    @guildtag_message.command(
        name="remove",
        aliases=["delete", "clear"],
        brief="Remove the guild tag message."
    )
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    @checks.cooldown()
    async def guildtag_message_remove(self, ctx):
        """
        Usage: {0}guildtag message remove
        Aliases: {0}gt message delete, {0}gt message clear
        Permission: Manage Guild
        Output:
            Removes the currently set guild tag adoption message.
        """
        query = """
                INSERT INTO guild_tags (server_id, message)
                VALUES ($1, NULL)
                ON CONFLICT (server_id)
                DO UPDATE SET message = NULL
                """
        await self.bot.cxn.execute(query, ctx.guild.id)
        await ctx.send(view=_simple("Guild tag message removed."), allowed_mentions=discord.AllowedMentions.none())

    @guildtag.command(
        name="config",
        aliases=["settings", "show"],
        brief="Show the guild tag settings for the guild."
    )
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    @checks.cooldown()
    async def guildtag_config(self, ctx):
        """
        Usage: {0}guildtag config
        Aliases: {0}gt config, {0}gt settings, {0}gt show
        Permission: Manage Guild
        Output:
            Displays the current guild tag configuration.
        """
        config = await self.get_guild_tag_config(ctx.guild.id)

        if not config:
            return await ctx.send(view=_simple("Guild tag system is not configured for this server."), allowed_mentions=discord.AllowedMentions.none())

        status = "Enabled" if config['enabled'] else "Disabled"
        channel = ctx.guild.get_channel(config['channel_id']) if config['channel_id'] else None
        channel_text = channel.mention if channel else "Not set"

        roles = [ctx.guild.get_role(rid).mention for rid in config['roles'] if ctx.guild.get_role(rid)]
        roles_text = "\n".join(roles) if roles else "None configured"

        message_text = config['message'] if config['message'] else "Not set"
        if len(message_text) > 1024:
            message_text = message_text[:1021] + "..."

        view = ui.LayoutView(timeout=None)
        container = ui.Container(accent_color=0xFFFFFF)
        container.add_item(ui.TextDisplay("## Guild Tag Configuration"))
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay(f"**Status** — {status}\n**Channel** — {channel_text}"))
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay(f"**Reward Roles**\n{roles_text}"))
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay(f"**Message**\n{message_text}"))
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay(f"-# {ctx.guild.name}"))
        view.add_item(container)
        await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

    @guildtag.command(
        name="list",
        brief="List all users that have the guild tag."
    )
    @checks.guild_only()
    @checks.cooldown()
    async def guildtag_list(self, ctx):
        """
        Usage: {0}guildtag list
        Alias: {0}gt list
        Output:
            Lists all users who have adopted the guild tag.
        """
        users = await self.get_guild_tag_users(ctx.guild.id)

        if not users:
            return await ctx.fail("No users have adopted the guild tag yet.")

        user_lines = []
        for record in users[:25]:
            member = ctx.guild.get_member(record['user_id'])
            if member:
                timestamp = discord.utils.format_dt(record['adopted_at'], style='R')
                user_lines.append(f"- {member.mention} — {timestamp}")

        total = len(users)

        view = ui.LayoutView(timeout=None)
        container = ui.Container(accent_color=0xFFFFFF)
        container.add_item(ui.TextDisplay("## Users with Guild Tag"))
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay("\n".join(user_lines) if user_lines else "No valid users found."))
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay(f"-# Total: {total} user{'s' if total != 1 else ''} — Showing {min(25, total)}"))
        view.add_item(container)
        await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        try:
            fresh_after = await self.bot.fetch_user(after.id)
            after_primary = getattr(fresh_after, 'primary_guild', None) or getattr(fresh_after, 'clan', None)
            before_primary = getattr(before, 'primary_guild', None) or getattr(before, 'clan', None)
        except Exception:
            after_primary = getattr(after, 'primary_guild', None) or getattr(after, 'clan', None)
            before_primary = getattr(before, 'primary_guild', None) or getattr(before, 'clan', None)

        before_id = getattr(before_primary, 'id', None) if before_primary else None
        after_id = getattr(after_primary, 'id', None) if after_primary else None
        before_enabled = getattr(before_primary, 'identity_enabled', False) if before_primary else False
        after_enabled = getattr(after_primary, 'identity_enabled', False) if after_primary else False

        if before_id == after_id and before_enabled == after_enabled:
            return

        for guild in self.bot.guilds:
            member = guild.get_member(after.id)
            if not member:
                continue

            config = await self.get_guild_tag_config(guild.id)
            if not config or not config['enabled']:
                continue

            was_match = before_enabled and before_id and str(guild.id) == str(before_id)
            is_match = after_enabled and after_id and str(guild.id) == str(after_id)

            if is_match and not was_match:
                query = "SELECT 1 FROM guild_tag_users WHERE server_id = $1 AND user_id = $2"
                already_tracked = await self.bot.cxn.fetchrow(query, guild.id, member.id)

                query = """
                        INSERT INTO guild_tag_users (server_id, user_id)
                        VALUES ($1, $2)
                        ON CONFLICT (server_id, user_id) DO NOTHING
                        """
                await self.bot.cxn.execute(query, guild.id, member.id)

                if config['roles']:
                    roles_to_add = [
                        guild.get_role(rid) for rid in config['roles']
                        if guild.get_role(rid) and guild.get_role(rid) not in member.roles
                        and guild.get_role(rid).position < guild.me.top_role.position
                    ]
                    if roles_to_add:
                        try:
                            await member.add_roles(*roles_to_add, reason="User adopted guild tag")
                        except Exception:
                            pass

                if not already_tracked and config['channel_id'] and config['message']:
                    channel = guild.get_channel(config['channel_id'])
                    if channel:
                        try:
                            message = config['message']
                            message = message.replace('{user.mention}', member.mention)
                            message = message.replace('{user.name}', member.name)
                            message = message.replace('{user.id}', str(member.id))
                            message = message.replace('{server.name}', guild.name)
                            container = ui.Container(accent_color=0xFFFFFF)
                            container.add_item(ui.TextDisplay(message))
                            view = ui.LayoutView(timeout=None)
                            view.add_item(container)
                            await channel.send(view=view, allowed_mentions=discord.AllowedMentions(users=True))
                        except Exception:
                            pass

            elif was_match and not is_match:
                query = "DELETE FROM guild_tag_users WHERE server_id = $1 AND user_id = $2"
                await self.bot.cxn.execute(query, guild.id, member.id)

                if config['roles']:
                    roles_to_remove = [
                        guild.get_role(rid) for rid in config['roles']
                        if guild.get_role(rid) and guild.get_role(rid) in member.roles
                        and guild.get_role(rid).position < guild.me.top_role.position
                    ]
                    if roles_to_remove:
                        try:
                            await member.remove_roles(*roles_to_remove, reason="User removed guild tag")
                        except Exception:
                            pass

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        await self.on_user_update(before._user, after._user)

"""
: ! Aegis !
    + Discord: itsfizys
    + Community: https://discord.gg/aerox (AeroX Development )
    + for any queries reach out Community or DM me.
"""
