import os
import time
import re
from slackclient import SlackClient
from collections import defaultdict
import datetime

# instantiate Slack client
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "do"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"
STUCK_OUTSIDE = defaultdict() # username : start time
STOP_TIME = 10
BOT_CHANNEL = 'CB9N7KQ5C' #channel id for the doorbelle-test channel. change as necessary

def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command, channel, and the sender's ID.
    """
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == starterbot_id:
                return message, event["channel"], event["user"]
    return None, None, None

def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def handle_command(command='', channel=None, sender=None, remind=False):
    
    global STUCK_OUTSIDE
    #for unknown commands
    default_response = ("""IDGI. :( Try any of these: \n
            \'@doorbelle ring\' or \'@doorbelle let me in\' to be let in, \n
            or \'@doorbelle stop\' if you\'ve been let in. \n
            I will automatically stop ringing for a user after {} minutes.""").format(str(STOP_TIME))

    #handling known commands
    response = None

    #for users who have already pinged the bot, this creates the reminder message
    if remind:
        response = '<!channel> let <@{}> in!'.format(sender)

    else:
        if command.lower().startswith('ring') or command.startswith('let me in'):
            response = 'Got it, <@{}>! I\'ll annoy everyone until you\'re let in. >:)'.format(sender)
            print ("added user {} to stuck users".format(sender))
            STUCK_OUTSIDE[sender] = datetime.datetime.now()

        elif command.lower().startswith('stop'):
            response = 'Yay, <@{}>! Glad they let you in.'.format(sender)
            if sender in STUCK_OUTSIDE.keys():
                STUCK_OUTSIDE.pop(sender)
                print ("removed {} from stuck users".format(sender))
            else:
                response = 'Hey, you never asked to be let in. Rude.'
        
        elif command.lower().startswith('ding'):
            response = 'DONG!'
   
        elif command.lower().startswith('got it'):
            response = 'Noted, <@{}>!'.format(sender)
            STUCK_OUTSIDE = defaultdict()
        
        elif command.lower().startswith('i love you'):
            response = 'I love you too, <@{}>! <3'.format(sender)

    # responds in either the channel where the message was sent or in the default bot channel
    slack_client.api_call(
        "chat.postMessage",
        channel=channel or BOT_CHANNEL,
        text=response or default_response
    )

if __name__ == "__main__":
    if slack_client.rtm_connect(with_team_state=False):
        print("doorbelle connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            command, channel, sender = parse_bot_commands(slack_client.rtm_read())
            if command:
                handle_command(command, channel, sender)
                print (channel)

            #iterate through the users who are stuck outside
            t = datetime.datetime.now()
            #print ('STUCK: {}'.format(STUCK_OUTSIDE.keys()))
            for user in STUCK_OUTSIDE.keys():
                diff = t - STUCK_OUTSIDE[user]
                t_diff = (divmod(diff.days * 86400 + diff.seconds, 60))
                if t_diff[0] == 10:
                    print ('suspending pings for user {}'.format(user))
                    STUCK_OUTSIDE.pop(user)
                elif t_diff[1] == 0:
                    print ('pinging for user {}'.format(user))
                    handle_command(sender=user, remind=True)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")
