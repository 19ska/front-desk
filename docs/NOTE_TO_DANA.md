# A note for Dana

Hi Dana,

The Front Desk is ready to try. Sign in, and the first thing you'll see answers your question: **the lobby is busiest
on Tuesdays and Wednesdays, around 9 am**. Below it is a chart of every weekday and hour, and the full list of visits,
which you can filter by dates and visit type and share as a link. Here's what I found along the way, and the decisions
I made for you to check.

## What I found in your files

**1. Two of your three admins would have been locked out.** In the list of people allowed in, Marcus's email has
capital letters and Ines's has spaces before and after it. A strict match would have refused both. The app now
matches emails the way a person would, ignoring capitals and stray spaces, so all eight people on the list can sign up.

**2. The lobby iPad recorded 58 sign-ins twice.** The same guest, same host, a few seconds apart, and the second copy
never signed out. It looks like a double tap. I've removed the copies, which leaves **1,953 real visits** between
1 July and 30 September. Left in, they'd have nudged every count up.

**3. There are no sign-ins at all from Monday 10 to Thursday 13 August.** Every other weekday has between 12 and 61.
I've treated those four days as missing rather than quiet, and wherever you look at a period that includes them, the
app says so in plain words. Was the iPad down that week?

A few other things worth knowing when you read the numbers:

- **Nearly half of guests (45%) never sign out.** So visit length is measured only for those who did: the typical
  visit is **1 hour 19 minutes**, based on 1,083 visits. The app says that next to the number.
- **The 9 am rush is your interview schedule.** Every interview starts in the 9 o'clock hour. Filter to guests or vendors
  and the busiest time moves to mid-to-late morning (10 am to noon).
- **Tuesday and Wednesday are a tie** (about 39–40 visits a day). A plain total makes Wednesday look busier only because
  the quarter has one more Wednesday than Tuesday, so the app compares the average per day instead.
- **Nobody signs in between 12 and 1.** I've assumed the desk closes for lunch.
- **Three hosts appear under two teams:** Rafael Mbeki (Sales and Engineering), Henrik Moreau (Engineering and
  Recruiting) and Idris Brandt (Engineering and Marketing). I count each visit under the team the iPad recorded.

## Who can see what, and why

- **You, Marcus and Ines** see everything: who came, their email and company, and who hosted them.
- **Sam, Priya, Jonas, Ruth and Kenji** see how busy the building is: dates, times, visit types and the host's team.
  They never see a visitor's name, email or company, **and they don't see the host's name either**, just the team.
  Hosts are named people too, and the team is enough to read how busy things are.
- **Everyone else** can't create an account.

These rules are enforced by the server, not just the screen. When Sam looks at visits, the names are never sent to
his computer at all, so there's nothing to uncover by poking at the page. Where a name would be, viewers simply don't
have that column. A single visit is titled by its type, like "Guest".

If someone who isn't on the list tries to sign up, they see: *"This email isn't on Brightline's access list. If you
think it should be, ask Dana."* I chose the friendly version because the people who hit it will mostly be colleagues
who mistyped. The only thing it tells a stranger is that their email isn't on a list of eight. Happy to make it vaguer
if you'd prefer.

Removing someone from the list takes effect the next time the app restarts, even if they're signed in.

## What's not real yet

This is a working prototype, not something to put real visitor data behind as is:
- Accounts are stored in a file on the computer running it. Passwords are scrambled, not stored as typed, but there's
  no secure connection (HTTPS), no password reset and no company sign-in.
- There are two test logins, for Dana and Sam, with passwords written in the instructions so it can be reviewed.

## What I'd do with real visitors' data

- Sign in with your company accounts (single sign-on), so access follows people joining and leaving.
- Keep a record of who looked at whose details.
- Delete visits after an agreed period.
- Hide counts that are so small they could point to one person (for example, "the one interview Legal hosted on 3 Sep").
- Serve it over HTTPS.

## Questions for you

1. What happened from 10 to 13 August?
2. Is the desk closed from 12 to 1?
3. Which team are Rafael, Henrik and Idris actually in?
4. Are the iPad's times in the office's local time? I've assumed they are.

## What I'd do next

Answer those four, then add a way to compare two periods side by side, and a weekly summary you could have emailed.

Best,
Skanda Gonur Nagaraj
