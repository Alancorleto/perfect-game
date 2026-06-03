from fastapi import status
from fastapi.testclient import TestClient

from tests.helpers import get_auth_headers, get_grade


# This test exercises the main event scoring flow through the public API.
# It creates an organizer account, signs in, creates the organizer's player
# profile, builds an event structure, creates playable content, connects
# that content and player to a score table, submits a score, and verifies that
# the score table results endpoint calculates the expected score and placement.
def test_create_score_table_score_and_results_end_to_end(client: TestClient):
    # Create an organizer user account.
    user_response = client.post(
        "/users",
        json={"email": "organizer@example.com", "password": "mypassword123"},
    )
    assert user_response.status_code == status.HTTP_200_OK

    # Authenticate as the organizer and keep the access token for protected routes.
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    # Create the organizer's player profile.
    player_response = client.post(
        "/players/",
        json={"nickname": "E2EPlayer", "country_code": "AR"},
        headers=headers,
    )
    assert player_response.status_code == status.HTTP_200_OK
    player_id = player_response.json()["id"]

    # Create the event owned by the organizer.
    event_response = client.post(
        "/events/",
        json={"name": "E2E Event", "country_code": "AR"},
        headers=headers,
    )
    assert event_response.status_code == status.HTTP_200_OK
    event_id = event_response.json()["id"]

    # Create a tournament inside the event.
    tournament_response = client.post(
        "/tournaments/",
        json={"name": "Main Tournament", "event_id": event_id},
        headers=headers,
    )
    assert tournament_response.status_code == status.HTTP_200_OK
    tournament_id = tournament_response.json()["id"]

    # Add the organizer to the tournament.
    add_organizer_response = client.post(
        f"/tournaments/{tournament_id}/invitations/{player_id}",
        headers=headers,
    )
    assert add_organizer_response.status_code == status.HTTP_204_NO_CONTENT

    # Create a round inside the tournament.
    round_response = client.post(
        "/rounds/",
        json={"name": "Qualifiers", "tournament_id": tournament_id},
        headers=headers,
    )
    assert round_response.status_code == status.HTTP_200_OK
    round_id = round_response.json()["id"]

    # Create a score-sum score table inside the round.
    score_table_response = client.post(
        "/score_tables/",
        json={
            "round_id": round_id,
            "levels": "S15",
            "qualifiers_count": 1,
            "format": "score_sum",
        },
        headers=headers,
    )
    assert score_table_response.status_code == status.HTTP_200_OK
    score_table_id = score_table_response.json()["id"]

    # Add the chart to the score table as the first score column.
    score_column_response = client.post(
        "/score_columns/",
        json={"score_table_id": score_table_id},
        headers=headers,
    )
    assert score_column_response.status_code == status.HTTP_200_OK
    score_column_id = score_column_response.json()["id"]

    # Create a chart for the column.
    chart_response = client.post(
        "/charts/",
        json={
            "song_name": "E2E Song",
            "mode": "single",
            "level": 15,
            "player_count": 1,
        },
        params={
            "score_column_id": score_column_id,
        },
        headers=headers,
    )
    assert chart_response.status_code == status.HTTP_200_OK
    chart_id = chart_response.json()["id"]

    # Add the organizer's player to the score table.
    add_player_response = client.post(
        f"/score_tables/{score_table_id}/players/bulk",
        json=[player_id],
        headers=headers,
    )
    assert add_player_response.status_code == status.HTTP_200_OK
    assert add_player_response.json()[0]["id"] == player_id

    # Start the round
    start_round_response = client.post(
        f"/rounds/{round_id}/start",
        headers=headers,
    )
    assert start_round_response.status_code == status.HTTP_200_OK
    assert start_round_response.json()["id"] == round_id

    # Submit a score for the player on the score table's first score column.
    score_response = client.post(
        "/scores/",
        json={
            "player_id": player_id,
            "chart_id": chart_id,
            "score_column_id": score_column_id,
            "value": 987654,
            "perfect": 100,
            "great": 5,
            "good": 1,
            "bad": 0,
            "miss": 0,
            "max_combo": 106,
            "kcal": 12.5,
            "grade": "SS",
            "stage_pass": True,
        },
        headers=headers,
    )
    assert score_response.status_code == status.HTTP_200_OK
    score_id = score_response.json()["id"]

    # Fetch the calculated score table results.
    results_response = client.get(f"/score_tables/{score_table_id}/results")
    assert results_response.status_code == status.HTTP_200_OK
    results = results_response.json()

    # Verify the score-sum result and placement for the only player in the score table.
    assert len(results) == 1
    assert results[0]["player_id"] == player_id
    assert results[0]["total_score"] == 987654
    assert len(results[0]["results"]) == 1
    assert results[0]["results"][0]["score_id"] == score_id
    assert results[0]["results"][0]["score_value"] == 987654
    assert results[0]["results"][0]["place"] == 1


# This test verifies the score-sum format with a late player insertion in a round.
# Steps:
# 1. Create and authenticate an organizer.
# 2. Create an event, tournament, round, and a score-sum score table with two charts (levels 15 and 16).
# 3. Create eight guest players and add them to the tournament and score table.
# 4. Start the round.
# 5. Enter scores for the first four player pairs (players 0-3) on both charts in two-player game order.
# 6. Insert a late player after the fourth player, add them to the tournament and score table, and reorder score table players to place the late player at index 4.
# 7. Continue entering scores for the remaining pairs (including the late player) and the final unpaired player.
# 8. Finish the round.
# 9. Fetch the score table results and verify that the ordering is by total score (sum of both charts) and not by input order, and that each player has results for both charts.
def test_score_sum_round_with_late_player_insert_end_to_end(client: TestClient):
    def create_chart(song_name: str, level: int, score_column_id: str) -> str:
        chart_response = client.post(
            "/charts/",
            json={
                "song_name": song_name,
                "mode": "single",
                "level": level,
                "player_count": 1,
            },
            params={
                "score_column_id": score_column_id,
            },
            headers=headers,
        )
        assert chart_response.status_code == status.HTTP_200_OK
        return chart_response.json()["id"]

    def create_score(player_id: str, chart_id: str, score_column_id: str, score: int):
        response = client.post(
            "/scores/",
            json={
                "player_id": player_id,
                "chart_id": chart_id,
                "score_column_id": score_column_id,
                "value": score,
                "perfect": score // 1000,
                "great": 0,
                "good": 0,
                "bad": 0,
                "miss": 1000 - (score // 1000),
                "max_combo": score // 1000,
                "kcal": 12.5,
                "grade": get_grade(score),
                "stage_pass": score >= 970000,
            },
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK

    # Create and authenticate the event organizer.
    user_response = client.post(
        "/users",
        json={"email": "organizer@example.com", "password": "mypassword123"},
    )
    assert user_response.status_code == status.HTTP_200_OK
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    # Create one event, one tournament, one round, and one score-sum score table.
    event_response = client.post(
        "/events/",
        json={"name": "Late Insert Event", "country_code": "AR"},
        headers=headers,
    )
    assert event_response.status_code == status.HTTP_200_OK
    event_id = event_response.json()["id"]

    tournament_response = client.post(
        "/tournaments/",
        json={"name": "Main Tournament", "event_id": event_id},
        headers=headers,
    )
    assert tournament_response.status_code == status.HTTP_200_OK
    tournament_id = tournament_response.json()["id"]

    round_response = client.post(
        "/rounds/",
        json={"name": "Final Round", "tournament_id": tournament_id},
        headers=headers,
    )
    assert round_response.status_code == status.HTTP_200_OK
    round_id = round_response.json()["id"]

    score_table_response = client.post(
        "/score_tables/",
        json={
            "round_id": round_id,
            "levels": "S15 & S16",
            "qualifiers_count": 4,
            "format": "score_sum",
        },
        headers=headers,
    )
    assert score_table_response.status_code == status.HTTP_200_OK
    score_table_id = score_table_response.json()["id"]

    score_column_s15_response = client.post(
        "/score_columns/",
        json={"score_table_id": score_table_id},
        headers=headers,
    )
    assert score_column_s15_response.status_code == status.HTTP_200_OK
    score_column_15_id = score_column_s15_response.json()["id"]

    score_column_s16_response = client.post(
        "/score_columns/",
        json={"score_table_id": score_table_id},
        headers=headers,
    )
    assert score_column_s16_response.status_code == status.HTTP_200_OK
    score_column_16_id = score_column_s16_response.json()["id"]

    # Create two different charts.
    chart_s15_id = create_chart("Single 15 Song", 15, score_column_15_id)
    chart_s16_id = create_chart("Single 16 Song", 16, score_column_16_id)

    # Create 8 guest players so none of them is the event organizer.
    player_ids = []
    for index in range(1, 9):
        player_response = client.post(
            f"/players/guest/{event_id}",
            json={"nickname": f"Player {index}", "country_code": "AR"},
            headers=headers,
        )
        assert player_response.status_code == status.HTTP_200_OK
        player_ids.append(player_response.json()["id"])

    add_tournament_players_response = client.post(
        f"/tournaments/{tournament_id}/players/bulk",
        json=player_ids,
        headers=headers,
    )
    assert add_tournament_players_response.status_code == status.HTTP_200_OK

    add_score_table_players_response = client.post(
        f"/score_tables/{score_table_id}/players/bulk",
        json=player_ids,
        headers=headers,
    )
    assert add_score_table_players_response.status_code == status.HTTP_200_OK

    # Start the round before scores are entered.
    start_round_response = client.post(f"/rounds/{round_id}/start", headers=headers)
    assert start_round_response.status_code == status.HTTP_200_OK
    assert start_round_response.json()["state"] == "in_progress"

    score_values = {
        player_ids[0]: (950000, 988000),
        player_ids[1]: (954000, 996000),
        player_ids[2]: (928000, 911000),
        player_ids[3]: (902000, 957000),
        player_ids[4]: (995000, 934000),
        player_ids[5]: (983000, 988000),
        player_ids[6]: (975000, 903000),
        player_ids[7]: (918000, 927000),
    }

    # Enter scores in two-player game order for the first two pairs.
    for player_a_id, player_b_id in [
        (player_ids[0], player_ids[1]),
        (player_ids[2], player_ids[3]),
    ]:
        create_score(
            player_a_id, chart_s15_id, score_column_15_id, score_values[player_a_id][0]
        )
        create_score(
            player_b_id, chart_s15_id, score_column_15_id, score_values[player_b_id][0]
        )
        create_score(
            player_a_id, chart_s16_id, score_column_16_id, score_values[player_a_id][1]
        )
        create_score(
            player_b_id, chart_s16_id, score_column_16_id, score_values[player_b_id][1]
        )

    # After player 4 has both scores, add a new player and move them to order index 4.
    late_player_response = client.post(
        f"/players/guest/{event_id}",
        json={"nickname": "Late Player", "country_code": "AR"},
        headers=headers,
    )
    assert late_player_response.status_code == status.HTTP_200_OK
    late_player_id = late_player_response.json()["id"]

    add_late_tournament_player_response = client.post(
        f"/tournaments/{tournament_id}/players/bulk",
        json=[late_player_id],
        headers=headers,
    )
    assert add_late_tournament_player_response.status_code == status.HTTP_200_OK

    add_late_score_table_player_response = client.post(
        f"/score_tables/{score_table_id}/players/bulk",
        json=[late_player_id],
        headers=headers,
    )
    assert add_late_score_table_player_response.status_code == status.HTTP_200_OK

    ordered_player_ids = [
        player_ids[0],
        player_ids[1],
        player_ids[2],
        player_ids[3],
        late_player_id,
        player_ids[4],
        player_ids[5],
        player_ids[6],
        player_ids[7],
    ]
    update_score_table_player_order_response = client.put(
        f"/score_tables/{score_table_id}/players/order",
        json=ordered_player_ids,
        headers=headers,
    )
    assert update_score_table_player_order_response.status_code == status.HTTP_200_OK
    assert [
        p["id"] for p in update_score_table_player_order_response.json()
    ] == ordered_player_ids

    score_values[late_player_id] = (996000, 954000)

    # Continue entering scores in two-player game order after the inserted player.
    for player_a_id, player_b_id in [
        (late_player_id, player_ids[4]),
        (player_ids[5], player_ids[6]),
    ]:
        create_score(
            player_a_id, chart_s15_id, score_column_15_id, score_values[player_a_id][0]
        )
        create_score(
            player_b_id, chart_s15_id, score_column_15_id, score_values[player_b_id][0]
        )
        create_score(
            player_a_id, chart_s16_id, score_column_16_id, score_values[player_a_id][1]
        )
        create_score(
            player_b_id, chart_s16_id, score_column_16_id, score_values[player_b_id][1]
        )

    # The late insertion leaves the final original player without a pair.
    create_score(
        player_ids[7], chart_s15_id, score_column_15_id, score_values[player_ids[7]][0]
    )
    create_score(
        player_ids[7], chart_s16_id, score_column_16_id, score_values[player_ids[7]][1]
    )

    # Finish the round after all scores are loaded.
    finish_round_response = client.post(f"/rounds/{round_id}/finish", headers=headers)
    assert finish_round_response.status_code == status.HTTP_200_OK
    assert finish_round_response.json()["state"] == "finished"

    # Fetch and verify final score-sum results are mixed by total score, not input order.
    results_response = client.get(f"/score_tables/{score_table_id}/results")
    assert results_response.status_code == status.HTTP_200_OK
    results = results_response.json()

    expected_totals = {
        player_ids[0]: score_values[player_ids[0]][0] + score_values[player_ids[0]][1],
        player_ids[1]: score_values[player_ids[1]][0] + score_values[player_ids[1]][1],
        player_ids[2]: score_values[player_ids[2]][0] + score_values[player_ids[2]][1],
        player_ids[3]: score_values[player_ids[3]][0] + score_values[player_ids[3]][1],
        late_player_id: score_values[late_player_id][0]
        + score_values[late_player_id][1],
        player_ids[4]: score_values[player_ids[4]][0] + score_values[player_ids[4]][1],
        player_ids[5]: score_values[player_ids[5]][0] + score_values[player_ids[5]][1],
        player_ids[6]: score_values[player_ids[6]][0] + score_values[player_ids[6]][1],
        player_ids[7]: score_values[player_ids[7]][0] + score_values[player_ids[7]][1],
    }

    expected_result_order = [
        player_ids[5],
        player_ids[1],
        late_player_id,
        player_ids[0],
        player_ids[4],
        player_ids[6],
        player_ids[3],
        player_ids[7],
        player_ids[2],
    ]

    assert len(results) == 9
    assert [result["player_id"] for result in results] == expected_result_order
    assert [result["total_score"] for result in results] == [
        expected_totals[player_id] for player_id in expected_result_order
    ]
    assert [result["player_id"] for result in results] != ordered_player_ids
    assert all(len(result["results"]) == 2 for result in results)
