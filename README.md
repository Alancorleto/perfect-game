# Perfect Game

Perfect Game is a backend API for organizing competitive rhythm game tournaments.

It brings organizers everything they need into one place, from managing tournament settings to submitting player scores.

## Features

- Support for multiple categories per tournament
- Rounds with different formats, including score sum, battle, and custom set
- Account management with authentication and password reset
- Guest players for people who don't have an account
- Image storage for tournament logos, player avatars, and song titles

## Motivation

I've been involved in the rhythm game scene since I was a kid, and over the years I've organized many tournaments myself.

A lot of that work was handled with spreadsheets, manual payment tracking, and a patchwork of tools that never quite fit the way rhythm game tournaments actually work. Those limitations were frustrating enough that I wanted to build something better: a platform designed to make organizing rhythm game tournaments as smooth and convenient as possible. Perfect Game is the result of that effort, turning a messy process into something much more organized, practical, and built for the scene.

## Quick Start

1. Open the live API documentation at [https://perfect-game-sandbox.fastapicloud.dev/docs](https://perfect-game-sandbox.fastapicloud.dev/docs).
2. Create an account by calling `POST /users`.
3. Use the `Authorize` button in the top-right corner of the FastAPI docs to log in with your credentials.
4. Test the available endpoints directly from the Swagger UI.

It's a sandbox environment, so feel free to experiment with the API 😄

## Usage

All the endpoints are documented in detail in the FastAPI Swagger UI. However, here is a quick overview of the typical flow for a tournament with one category and one round.

1. Create a user.
2. Log in.
3. Create a tournament.
4. Add a category
5. Create one or more guest players to play the category.
6. Create one round for the category.
7. Create a score table for the round.
8. Create one or more score columns for the table.
9. Start the round.
10. Submit scores.
11. Check the table results to see the calculated standings.

### Additional functionality

- Upload images for tournament banners, player avatars, and chart titles.
- Configure round formats to score sum or battle.
- Invite registered players to join a tournament.
- If you are a player, request to join a tournament.
- Search already existing chart titles by song name, to save the user the effort of uploading a new one.
- Create chart columns for formats in which each player chooses their own chart to play.
- Reset user password.

## Future Improvements

- Support for player teams
- Support for custom scoring columns

## Contributing

<!-- How to run the project locally, tests, and contribution guidance. -->
