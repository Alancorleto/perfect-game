# Users
A user is a registered person using the application.

A user can manage **events** and their **player profile**.

To create a user account, use the `POST /users` endpoint.

To authenticate in the Swagger UI docs, press the **Authorize** button in the top right corner.

Otherwise, use the `/token` endpoint to authenticate.

Users can also:
- Refresh their **access token** via a refresh token
- Revoke their **refresh token**
- Request a **password reset**

# Players
A player is the profile of a competitor within a tournament.

There are two types of players:
- **Registered players**: These represent the public profile of a **user**.
- **Unregistered players**: These are created as **temporary guests** for an **event** when a competitor is not registered as a user.

Typically, a user creates a player profile when they register.

# Events
An event is a collection of competitions that happen at a specified time and location.

An event is composed of one or more **tournaments**.

An event has one or more **organizers**.

Each organizer has permissions to manage all the resources related to the event: tournaments, rounds, score tables, charts, and guest players.

# Tournaments
A tournament is a competition that happens within an **event**. It contains an ordered list of **rounds**.

A tournament has one or more **rounds**. Each round has a specific order.

An organizer can add **guest players** to a tournament.

An organizer can **invite** a player with a registered account to a tournament, and the player can **accept** or **decline** the invitation.

A player can **request to join** a tournament, and an organizer can **accept** or **decline** the request.

An organizer can **track** wether a player has paid their entry fee.

# Rounds
A round is a stage of competition within a **tournament**. It contains a collection of **score tables**.

A round has one or more **score tables** associated with it (multiple score tables are needed for battle formats).

A round is always in one of the following **states**:
- not_started
- in_progress
- paused
- finished

# Score Tables
A score table is where players compare their scores against each other within a **round**. It contains a list of players and a list of **score columns**.

A score table is composed of the **players** that are competing inside it and the **score columns** that contain the actual scores.

A score table can be in any of the following formats:
- **score_sum**: the final score is the sum of the scores of the players for each score column
- **battle**: the final score is the number of wins of the players for each score column

# Score Columns
A score column contains a list of scores that are meant to be compared against each other.

A score column is always associated with a **score table** and has an **order_index**.

A score column can have an optional associated **chart** which represents the chart that is meant to be played.

If a chart is not specified, the score column can have an associated **chart column** which represents the chart that each individual player played.

# Scores
A score represents a **player**'s performance for a **score column**.

The actual value of the score is stored in `value`.

The other values (`perfect`, `great`, `good`, `bad`, `miss`, `max_combo`) represent the details of the score.

A score can have a grade, which is one of the following: F, D, C, B, A, A+, AA, AA+, AAA, AAA+, S, S+, SS, SS+, SSS, SSS+.

# Chart Columns
A chart column is used when a **score column** has no **chart** associated with it, for example, when each player played a chart of their own choice.

A chart column represents **which chart** each player played for the associated score column.

# Charts
A chart is what competitors play to compare scores against each other.

A chart must be associated with any of the following:
- A **score column**, which represents the chart that must be played in that column
- A combination of **chart column** and **player**, which represents the chart that was played in that column by that player

A chart has a song name, a player count, a mode, a level difficulty, and a title image which can be uploaded by an organizer.
