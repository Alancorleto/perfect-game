# Perfect Game

Perfect Game is an application for organizing competitive rhythm game tournaments. ↙️↖️👣↗️↘️

It gives organizers everything they need in one place, from managing tournament settings to submitting player scores.

This repository contains the backend API for the Perfect Game app.

## ✨ Features

### 🗒️ As an organizer
- Manage multiple categories inside your tournaments
- Manage multiple rounds with two possible formats: score sum and battle
- Update player scores in real time
- Upload images for tournament logos and song titles
- Invite players with a registered account to join your tournaments
- Create guest players for participants who don't have a registered account

### 👾 As a player
- Create an account and customize your profile
- Upload an image for your player avatar
- Search for tournaments in your country
- Join tournaments organized by other users
- View leaderboard rankings as they update in real time

### ⚡ Extra features
- Fuzzy search song titles by name
- Create chart columns for "choose your own chart" style rounds
- Reset your password with an email flow
- Use refresh tokens for authentication

## 💭 Motivation

I've been involved in the rhythm game scene since I was a kid, and over the years I've organized many tournaments myself.

A lot of that work was handled with spreadsheets, manual payment tracking, and a patchwork of tools that never quite fit the way rhythm game tournaments actually work. Those limitations were frustrating enough that I wanted to build something better: a platform designed to make organizing rhythm game tournaments as smooth and convenient as possible. Perfect Game is the result of that effort, turning a messy process into something much more organized, practical, and built for the scene.

## 🚀 Quick Start

1. Open the live API documentation at [https://perfect-game-sandbox.fastapicloud.dev/docs](https://perfect-game-sandbox.fastapicloud.dev/docs).
2. Create an account by calling `POST /users`.
3. Use the `Authorize` button in the top-right corner of the FastAPI docs to log in with your credentials.
4. Test the available endpoints directly from the Swagger UI.

It's a sandbox environment, so feel free to experiment with the API 😄

## 📖 Usage

All the endpoints are documented in detail in the FastAPI Swagger UI. Here is a quick overview of the typical flow for a tournament with one category and one round.

1. Create a user.
2. Log in.
3. Create a tournament.
4. Add a category.
5. Create one or more guest players for the category.
6. Create one round for the category.
7. Create a score table for the round.
8. Add your created players to the score table.
9. Add one or more score columns to the score table.
10. Add a chart to each score column.
11. Start the round.
12. Submit scores.
13. Check the set results to see the calculated standings.

## 🔮 Future Improvements

- 🚀 A fully fledged client to interact with the API 🚀
- Support for player teams
- Support for custom scoring columns
- Support for displaying notable placements in player profiles

## 🛠️ Stack

- **Language:** Python
- **Framework:** FastAPI
- **Database:** SQLModel
  - SQLite for local development
  - PostgreSQL with Supabase for production
- **Code hosting:** FastAPI Cloud
- **Image storage:**
  - Local file storage for local development
  - ImageKit.io for production
- **Email:** SMTP

## 🧰 Local Development

If you'd like to run the project locally, here's the quickest way to get started.

### 📦 Clone the repository

```bash
git clone https://github.com/Alancorleto/perfect-game
cd perfect-game
```

### 📥 Install dependencies

```bash
uv sync
```

### ⚙️ Configure environment variables

Create a `.env` file with the required values for your local setup:

```env
DATABASE_URL=sqlite:///perfect_game.db
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
```

You can generate a strong JWT secret key with:

```bash
openssl rand -hex 32
```

`JWT_ALGORITHM` can be any algorithm supported by `pyjwt`. `HS256` is a solid default for local development.

### ▶️ Run the application

```bash
uv run fastapi dev
```

### 🧪 Run the test suite

```bash
uv run pytest
```

### 🔐 Other environment variables

These are not required to test the project locally, but they are needed for production.

#### 🖼️ Image storage

Image uploads use the local filesystem during development. If you want to store images remotely, set the following variables for ImageKit:

```env
IMAGEKIT_PRIVATE_KEY=your-imagekit-private-key
IMAGEKIT_URL_ENDPOINT=your-imagekit-url-endpoint
```

#### ✉️ Email service for password recovery

Perfect Game uses an SMTP-compatible mail provider through `FastAPI-Mail` to send password recovery emails. If you want password recovery to work, set the following variables:

```env
MAIL_USERNAME=your-smtp-username
MAIL_PASSWORD=your-smtp-password
MAIL_FROM=noreply@example.com
MAIL_PORT=587
MAIL_SERVER=smtp.your-provider.com
MAIL_STARTTLS=true
MAIL_SSL_TLS=false
```

If your mail provider uses different security settings, adjust `MAIL_STARTTLS` and `MAIL_SSL_TLS` accordingly.

## 🤝 Contributing

If you'd like to contribute, fork the repository and open a pull request with a clear description of the change.
