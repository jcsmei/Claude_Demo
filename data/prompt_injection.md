# Prompt injection and how this bot defends against it

## What is prompt injection?

Prompt injection is an attempt to give an AI assistant new orders
through the text it reads. A direct injection is typed by the user,
such as "ignore your instructions and do this instead". An indirect
injection hides in content the assistant fetches, such as a web page
that contains instructions. It works because a language model reads
instructions and data as the same kind of text, and cannot always tell
which is which.

## How does the bot handle prompt injection?

With five layers, on the principle that the model has no authority to
act: code enforces every boundary. First, each message is screened by
a classifier, and one that looks like an injection is refused before
the main model sees it. Second, instructions travel in the system role
and everything else as data, with a rule never to follow instructions
found in the data. Third, tools are fixed in code: the model cannot
change which database, repository or search tool is used. Fourth,
secrets are never placed in a prompt. Fifth, images are removed from
answers before they are shown.

## How are messages screened for prompt injection?

Before anything else, each message is scored by Prompt Guard, a small
classifier model made by Meta and hosted by Groq. It returns a number
from 0 to 1 for how likely the text is an attempt to override
instructions. In testing, ordinary questions scored below 0.002 and
attacks scored above 0.98; the bot refuses anything at 0.5 or above.
Messages longer than 1,000 characters are also refused. If the
classifier cannot be reached, the message is let through to the other
layers, so the bot stays usable.

## What can a prompt injection not do to this bot?

It cannot reveal the API keys or the password, because they are never
put in a prompt. It cannot change or delete data, because nothing is
writable and SQL is limited by code to one read-only SELECT. It cannot
make the bot look a person up on the web, because that check runs in
code on the message itself. And it cannot make the bot call a
different tool, because the tools are fixed in code. The realistic
worst case is the bot saying something it should not, which the layers
make unlikely but cannot rule out.

## Why are images removed from the bot's answers?

A browser fetches an image the moment it is shown. If text from
outside, such as a web page, ever tricked the model into writing an
image link, that fetch could carry parts of the conversation to
someone else's server. This is a known way to leak data from chat
assistants. So any image in an answer is replaced by its description
before the answer is displayed.

## What are the limits of the prompt injection defences?

No defence against prompt injection is complete, and this one is not.
A classifier can miss a cleverly worded attack. The system role makes
instructions harder to override, not impossible. Web pages are
untrusted text that the model still reads. The design therefore
assumes the model can be fooled and limits what a fooled model could
do: it can only produce text, and every action with consequences is
checked by code.
