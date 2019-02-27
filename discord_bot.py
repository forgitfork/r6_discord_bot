""" This bot checks stats from the R6Stats website and pastes them into Discord
when called.

Options:
    > !help - Provides a list of available commands.

Note:
The stats are accessed from r6.tracker.network by using the uPlay username.
Local usernames can be stored in the users.py as a dictionary. This allows
Discord to know which user is requesting the stats, otherwise a username must
be passed to the bot.
"""

import discord
import random
import bs4
import requests
from users import users
from discord.ext.commands import Bot
from discord import Game

client = Bot(command_prefix='!')  # The prefix used to summon the bot

# This is the Bot Token from Discord and saved into tokens.py
TOKEN = 'add_server_token_here'


# Webscraper function, with required arguments passed from the call.
async def data_request(context, casual_ranked, username_local):
    # Here the unique identifier is input into the URL to get the correct page
    r = requests.get('https://r6.tracker.network/profile/pc/{}'.
                     format(username_local.lower()))
    scrape = bs4.BeautifulSoup(r.text, 'html.parser')

    if r.status_code == 200:
        # If the connection is successful, begin scrape
        await webscrape(context, casual_ranked, scrape)

    elif r.status_code == 404:
        # If the webscraper hasn't collect the correct information, return error.
        print('>Check failed. 404 on the username.')
        await error_message_404(context, username_local)

    else:
        # Handles errors other than 404.
        print(f'>Check failed. Status code: {r.status_code}.')
        await error_message(context, username_local)


# A fun way of distracting the user if the webscrape fails with a non-404 error.
# round(random) function used to pick a float between 1-5 and round to 2 decimal points.
async def error_message(context, author):
    msg = 'I can\'t access the tracker site right now so I\'ll just guess your K/D instead.'
    msg2 = f'User {author} has a KD of {round(random.uniform(1, 5), 2)} on Rainbow 6: Siege'
    await client.send_message(context.message.channel, msg)
    await client.send_message(context.message.channel, msg2)


# Provides an error message whent the website responds with a 404
async def error_message_404(context, author):
    msg = (f'Either user {author.title()} does not exist or the website is '
           'displaying a 404 error.')
    msg2 = 'Please check the spelling and try again.'
    await client.send_message(context.message.channel, msg)
    await client.send_message(context.message.channel, msg2)


async def webscrape(context, casual_ranked, scrape):
    # Creates blank lists for storing required data.
    label, count, data, total = [[] for i in range(4)]

    cas_rank_gen = ['Empty', 'Overview', 'Overview2', 'Current Operation',
                    'General', 'Casual', 'Ranked']

    for element in scrape.select('.trn-scont__content'):
            for gen in element.select('.trn-card__content'):
                for stats_list in gen.select('.trn-defstats'):
                    for stat_label in stats_list.select('.trn-defstat__name'):
                        label.append(stat_label.get_text(strip=True))
                    for stat_count in stats_list.select('.trn-defstat__value'):
                        count.append(stat_count.get_text(strip=True))
                data.append(dict(zip(label, count)))

    total.append(dict(zip(cas_rank_gen, data)))

    # Pulls the users uPlay profile image
    for profile in scrape.select('.trn-profile-header__avatar'):
        for link in profile.find_all('img', src=True):
            profile_url = link['src']

    # Default status is unranked.
    current_rank = 'Not Ranked'
    for rating in scrape.find_all(style='width: 50px; margin-right: 14px;'):
        for rank in rating.select('img'):
            current_rank = rank['title']

    # This pulls the username and correct formatting from the website.
    for username in scrape.select('.trn-profile-header__name'):
        username_web = str(username.get_text())

    # Pulls the name of the most played character from inside an image link.
    for mostplayed in scrape.select('.trn-defstat__value'):
        for source in mostplayed.find_all('img', src=True, limit=1):
            waifu = source['title'].title()
            # Takes the operator name and adds it to a URL to pull a picture of that Op
            waifu_picture = f'https://cdn.r6stats.com/figures/{waifu.lower().replace("ä", "a")}_figure.png'

    requested_cas_rank = total[0][f'{casual_ranked.title()}']
    # If the user has not played ranked/casual then the 'Time Played' stat
    # is blank. This checks the length and makes it 0 if nothing is there
    if len(requested_cas_rank['Time Played']) == 0:
        requested_cas_rank['Time Played'] = 0

    # Passes all information to the embed_creator for message creation.
    await embed_creator(context, casual_ranked, username_web, profile_url,
                        requested_cas_rank['Time Played'], requested_cas_rank['Kills'],
                        requested_cas_rank['Deaths'], requested_cas_rank['KD'],
                        requested_cas_rank['Win %'], waifu, waifu_picture, current_rank)


# Embed creator takes the variables established in the webscraper
# prettyfies the results and sends them as a message.
async def embed_creator(context, casual_ranked, username, profile_url,
                        time_played, kills, deaths, kd, wl, waifu,
                        waifu_picture, current_rank):
    embed=discord.Embed(title=f"R6 Stats Checker | {casual_ranked.title()}", color=0xe3943c)
    embed.set_thumbnail(url=profile_url)
    embed.add_field(name="Username", value=username, inline=True)
    embed.add_field(name="Time Played", value=time_played, inline=True)
    embed.add_field(name="Kills", value=kills, inline=True)
    embed.add_field(name="Deaths", value=deaths, inline=True)
    embed.add_field(name="K/D Ratio", value=kd, inline=True)
    embed.add_field(name="W/L %", value=wl, inline=True)
    embed.add_field(name="Waifu", value=waifu, inline=True)
    embed.add_field(name="Rank", value=current_rank, inline=True)
    embed.set_image(url=waifu_picture)
    embed.set_footer(text="*Want to see how your stats compare to your friends? \
    Head to leaderboard.codeishard.co.uk.*")
    await client.send_message(context.message.channel, embed=embed)


# R6 stats checker
@client.command(pass_context=True,
                aliases=['R6', 'stats', 'Stats'],
                brief='Use the argument casual/ranked or a uplay username',
                description='Provides stats from the R6Stats website')
async def r6(context, casual_ranked='general', search_cas_rank='general'):
    # Turns the author name into a string so it can be checked against the list
    u = str(context.message.author)  # Print for the log showing who triggered the bot.
    print(f'>Stats check by user {u} | {casual_ranked.title()}')
    # Checks if the argument called is either casual or ranked.
    if casual_ranked.lower() in {'casual', 'ranked', 'general'}:
        # If the author is present in the list, continue with codeself.
        # Otherwise this author hasn't been created. Prompt contact with admin.
        if u in users:
            username_local = users[u][0]  # username_local stored for checking later
            # Pass this information to the data_request() func.
            await data_request(context, casual_ranked, username_local)
        else:
            print('>Check failed. Is the username on the list?')
            msg = ('I\'m afraid I don\'t have your ID stored for Rainbow 6.'
                   ' Please speak to the admin to get you added to the list.')
            await client.say(msg)

    # If the argument is not casual/ranked then it expects it to be a username
    # and passes it as such
    else:
        username_local = casual_ranked.lower()
        if search_cas_rank.lower() in {'casual', 'ranked', 'general'}:
            casual_ranked = search_cas_rank.lower()
            await data_request(context, casual_ranked, username_local)
        else:
            print('>Attempted user search but passed something other than casual, ranked or general.')
            msg = 'When searching for a user, please only pass `casual`, `ranked`, or `general` as additional arguments.'
            msg2 = 'Please try again.'
            await client.say(msg)
            await client.say(msg2)


# Helpful message printed when the code is first run
@client.event
async def on_ready():
    await client.change_presence(game=Game(name="with humans"))
    print('Logged in as:')
    print(client.user.name)
    print(client.user.id)
    print('------')

client.run(TOKEN)
