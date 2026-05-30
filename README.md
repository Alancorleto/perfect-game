# Perfect Game

Perfect Game is an app for organizing competitive rhythm game tournaments.

It brings organizers everything they need into one place, from managing tournament settings to submitting player scores.

This is the backend API for the Perfect Game app.

## Features

### As an organizer
- Manage multiple categories inside your tournaments
- Manage multiple rounds with two different possible formats: score sum and battle
- Update player scores in real time
- Upload images for your tournament logos and song titles
- Invite players with a registered account to join your tournaments
- Create guest players for participants that don't have a registered account

### As a player
- Create an account and customize your profile
- Upload an image for your player avatar
- Search for tournaments in your country
- Join tournaments organized by other users
- View leaderboard rankings as they are updated in real time

### Extra features
- Fuzzy search for song titles by song name
- Create chart columns for "choose your own chart" style rounds
- Reset your password
- Use refresh tokens for authenticating 

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

All the endpoints are documented in detail in the FastAPI Swagger UI. Here is a quick overview of the typical flow for a tournament with one category and one round.

1. Create a user.
2. Log in.
3. Create a tournament.
4. Add a category.
5. Create one or more guest players for the category.
6. Create one round for the category.
7. Create a set for the round.
8. Add one or more charts to the set.
9. Start the round.
10. Submit scores.
11. Check the set results to see the calculated standings.

## Future Improvements

- 🚀 A fully fledged client to talk with the API 🚀
- Support for player teams
- Support for custom scoring columns
- Support for displaying notable placements in player profile

## Contributing

If you'd like to run the project locally or contribute changes, here's the quickest way to get started.

### Clone the repository

```bash
git clone https://github.com/your-username/perfect-game.git
cd perfect-game
```

### Install dependencies

```bash
uv sync
```

### Configure environment variables

Create a `.env` file with the required values for your local setup, including `DATABASE_URL`, `JWT_SECRET_KEY`, and any mail or image storage settings you want to use.

### Run the application

```bash
uv run fastapi dev
```

### Run the test suite

```bash
uv run pytest
```

If you'd like to contribute, fork the repository and open a pull request with a clear description of the change.
