import asyncio
import websockets
import json
import motor.motor_asyncio
from datetime import datetime
import random
import copy
import logging
import re

# win,fail,tie

import serial
from ip_config import get_ip_address, get_websocket_url
# Serial port configuration for shoe reader
SERIAL_PORT = "COM1"  # Adjust this to match your serial port
BAUD_RATE = 9600
ser = None

# MongoDB setup
MONGO_URI = "mongodb://localhost:27017"
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client["blackjack_db"]
results_collection = db["game_results"]

connected_clients = set()

# Store the last 5 game states for undo functionality
previous_game_states = []

# Serial port setup (adjust as needed)
# ser = None
# try:
#     ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)  # Use consistent SERIAL_PORT
# except Exception as e:
#     print(f"Serial port not available: {e}")

def log_function_call(func_name, *args, **kwargs):
    """Helper function to log function calls with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    args_str = ", ".join([str(arg) for arg in args])
    kwargs_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    params = ", ".join(filter(None, [args_str, kwargs_str]))
    print(f"[{timestamp}] Function called: {func_name}({params})")

def create_deck():
    """Creates 6 standard 52-card decks for Blackjack"""
    log_function_call("create_deck")
    ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K"]
    suits = ["S", "D", "C", "H"]
    deck = [rank + suit for rank in ranks for suit in suits] * 6
    random.shuffle(deck)
    return deck

# Global game state
game_state = {
    "deck": create_deck(),
    "round_number": 0,
    "min_bet": 0,
    "max_bet": 0,
    "dealer": {"cards": [], "total": 0, "status": "playing", "result": "", "live_function_hand": ""},
    "players": {
        "player1": {
            "hands": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split1": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split1_status": 0,
            "split2": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split2_status": 0,
            "status": 0,
            "insurence": 0,
            "surrender": 0,
            "even_money": 0,
            "live_function_player": ""
        },
        "player2": {
            "hands": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split1": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split1_status": 0,
            "split2": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split2_status": 0,
            "status": 0,
            "insurence": 0,
            "surrender": 0,
            "even_money": 0,
            "live_function_player": ""
        },
        "player3": {
            "hands": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split1": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split1_status": 0,
            "split2": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split2_status": 0,
            "status": 0,
            "insurence": 0,
            "surrender": 0,
            "even_money": 0,
            "live_function_player": ""
        },
        "player4": {
            "hands": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split1": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split1_status": 0,
            "split2": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split2_status": 0,
            "status": 0,
            "insurence": 0,
            "surrender": 0,
            "even_money": 0,
            "live_function_player": ""
        },
        "player5": {
            "hands": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split1": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split1_status": 0,
            "split2": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split2_status": 0,
            "status": 0,
            "insurence": 0,
            "surrender": 0,
            "even_money": 0,
            "live_function_player": ""
        },
        "player6": {
            "hands": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split1": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split1_status": 0,
            "split2": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split2_status": 0,
            "status": 0,
            "insurence": 0,
            "surrender": 0,
            "even_money": 0,
            "live_function_player": ""
        }
    },
    "max_players": 7,
    "current_player": None,  # Currently selected player
    "selected_hand": None,   
    "game_phase": "waiting",
    "table_number": 1,
    "auto_split_draw_card": 0,
    "rounds_played_in_game": 1,
    "mode": "live",
    "action_history": [],
    "auto_reshuffle_threshold": 52,
    "split_fire_state": 0, # FOR LIVE MODE ONLY
    "split_current_pointer": 0, # FOR LIVE MODE ONLY
    "split_call_live_previous_counter": 0, # FOR LIVE MODE ONLY 0: not split, 1: split, 2: split and next turn
    "evaluate_game": False,  # Track whether game has been evaluated
    "next_manual_counter": 0,  # no 2 next_turn occur during round 0
    "manual_distribution_count": 0,  # each player gets 2 cards only in round 0
    "all_done": 0, # 0: not all done (insurence or surrender or even money), 1: all done
}

def get_card_value(card):
    """Returns numerical value of a card"""
    log_function_call("get_card_value", card=card)
    rank = card[:-1]
    return 10 if rank in ['J', 'Q', 'K', 'T'] else 11 if rank == 'A' else int(rank)

def calculate_hand_value(cards):
    """Calculates best possible hand value, handling Aces"""
    log_function_call("calculate_hand_value", cards=cards)
    total = sum(get_card_value(card) for card in cards)
    aces = sum(1 for card in cards if card[:-1] == 'A')
    
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total

def is_blackjack(cards):
    log_function_call("is_blackjack", cards=cards)
    return len(cards) == 2 and calculate_hand_value(cards) == 21

def is_split_hand(player_data, split_level=0):
    """Check if a hand is a result of a split"""
    log_function_call("is_split_hand", player_data=player_data, split_level=split_level)
    if split_level == 0:
        # Main hand - check if any splits are active
        return player_data.get("split1_status") == 1 or player_data.get("split2_status") == 1
    elif split_level == 1:
        # Split1 hand
        return player_data.get("split1_status") == 1
    elif split_level == 2:
        # Split2 hand
        return player_data.get("split2_status") == 1
    return False

def is_bust(cards):
    log_function_call("is_bust", cards=cards)
    return calculate_hand_value(cards) > 21

def can_split(cards):
    """Check if cards can be split - must be same rank (number/letter), suit does not matter"""
    log_function_call("can_split", cards=cards)
    return len(cards) == 2 and cards[0][:-1] == cards[1][:-1]  # Only compare rank, not suit

def can_surrender(player_cards, dealer_upcard):
    """Check surrender conditions"""
    log_function_call("can_surrender", player_cards=player_cards, dealer_upcard=dealer_upcard)
    return (len(player_cards) == 2 and 
            not is_blackjack(player_cards) and 
            dealer_upcard[:-1] not in ['A'])

def should_auto_reshuffle():
    log_function_call("should_auto_reshuffle")
    return len(game_state["deck"]) < game_state["auto_reshuffle_threshold"]

async def save_action_history(action, data):
    """Save action for undo functionality"""
    log_function_call("save_action_history", action=action, data=data)
    import copy
    # Save a deep copy of the current game state to previous_game_states
    previous_game_states.append(copy.deepcopy(game_state))
    if len(previous_game_states) > 10:
        previous_game_states.pop(0)  # Remove the oldest state

    # Only store action and data in action_history (no heavy snapshot)
    game_state["action_history"].append({
        "action": action,
        "data": copy.deepcopy(data),
        "timestamp": datetime.utcnow(),
    })
    if len(game_state["action_history"]) > 10:
        game_state["action_history"] = game_state["action_history"][-10:]

def serialize_game_state():
    """Convert game state to JSON format"""
    log_function_call("serialize_game_state")
    # Update first_active_player_hand in game_state
    game_state["first_active_player_hand"] = get_first_active_player_hand()
    return {
        "deck_count": len(game_state["deck"]),
        "dealer": {
            "cards": game_state["dealer"]["cards"],
            "total": game_state["dealer"]["total"],
            "status": game_state["dealer"]["status"],
            "result": game_state["dealer"].get("result", ""),
            "live_function_hand": game_state["dealer"].get("live_function_hand", "")
        },
        "players": {
            pid: {
                "hands": pdata["hands"],
                "split1": pdata["split1"],
                "split1_status": pdata["split1_status"],
                "split2": pdata["split2"],
                "split2_status": pdata["split2_status"],
                "status": pdata["status"],
                "insurence": pdata.get("insurence", 0),
                "surrender": pdata.get("surrender", 0),
                "even_money": pdata.get("even_money", 0),
                "live_function_player": pdata.get("live_function_player", "")
            }
            for pid, pdata in game_state["players"].items()
        },
        "game_phase": game_state["game_phase"],
        "current_player": game_state["current_player"],
        "selected_hand": game_state["selected_hand"],
        "table_number": game_state["table_number"],
        "round_number": game_state["round_number"],
        "min_bet": game_state["min_bet"],
        "max_bet": game_state["max_bet"],
        "mode": game_state["mode"],
        "rounds_played_in_game": game_state["rounds_played_in_game"],
        "auto_split_draw_card": game_state["auto_split_draw_card"],
        "evaluate_game": game_state["evaluate_game"],
        "split_fire_state": game_state["split_fire_state"],
        "split_call_live_previous_counter": game_state["split_call_live_previous_counter"],
        "next_manual_counter": game_state["next_manual_counter"],
        "split_current_pointer": game_state["split_current_pointer"],
        "manual_distribution_count": game_state["manual_distribution_count"],
        "first_active_player_hand": game_state["first_active_player_hand"],
        "all_done": game_state["all_done"]
    }

async def broadcast(message):
    """Send message to all connected clients"""
    log_function_call("broadcast", message=message)
    print("\n=== BROADCAST STARTED ===")
    print(f"Message to broadcast: {message}")
    print(f"Number of connected clients: {len(connected_clients)}")
    
    if connected_clients:
        try:
            print("Attempting to broadcast to all clients...")
            await asyncio.gather(
                *[client.send(json.dumps(message)) for client in connected_clients],
                return_exceptions=True
            )
            print("Broadcast completed successfully")
        except Exception as e:
            print(f"Error during broadcast: {str(e)}")
            print("Error type:", type(e))
            import traceback
            print("Traceback:", traceback.format_exc())
    else:
        print("No connected clients to broadcast to")
    print("=== BROADCAST COMPLETED ===\n")

async def handle_connection(websocket):
    """Handle new client connections"""
    log_function_call("handle_connection", websocket=websocket.remote_address)
    connected_clients.add(websocket)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] Client connected: {websocket.remote_address}")

    # Send current game state immediately on connection
    await websocket.send(json.dumps({
        "action": "update_game_state",
        "game_state": serialize_game_state()
    }))

    # If game is in progress, also send turn update
    if game_state["game_phase"] == "playing":
        await websocket.send(json.dumps({
            "action": "turn_updated",
            "current_player": game_state["current_player"],
        "game_state": serialize_game_state()
    }))

    # Action handlers mapping
    action_handlers = {
        "set_game_mode": lambda d: handle_set_game_mode(d.get("mode")),
        "reshuffle": lambda d: handle_reshuffle(),
        "activate_player": lambda d: handle_activate_player(d.get("player_id")),
        "remove_player": lambda d: handle_remove_player(d.get("player_id")),
        # "double_player": lambda d: handle_hit_player(d.get("player_id"), d.get("hand_index", 0), d.get("card")),
        "hit_player": lambda d: handle_hit_player(d.get("player_id"), d.get("hand_index", 0), d.get("card")),
        "hit_dealer": lambda d: handle_hit_player("dealer", 0, d.get("card")),
        "stand_player": lambda d: handle_next_turn(),
        "split_player_live": lambda d: handle_split_player_live(d.get("player_id")),
        "split_player_auto": lambda d: handle_split_player_auto(d.get("player_id")),
        "reset_round": lambda d: handle_reset_round(),
        "undo_last": lambda d: handle_undo_last(),
        "set_table_number": lambda d: handle_set_table_number(d.get("table_number")),
        "reset_game": lambda d: handle_reset_game(),
        "next_turn": lambda d: handle_next_turn(),
        "start_game": lambda d: handle_start_game(),
        "live_start": lambda d: handle_live_start(),
        "distribute_cards": lambda d: handle_distribute_cards_auto(),
        "handle_insurence": lambda d: handle_insurence(d.get("player_id")),
        "dealer_auto_play": lambda d: handle_dealer_value_less_then_17(),
        "evaluate_game": lambda d: evaluate_game(),
        "activate_split1": lambda d: handle_activate_split1(d.get("player_id")),
        "activate_split2": lambda d: handle_activate_split2(d.get("player_id")),
        "deactivate_split1": lambda d: handle_deactivate_split1(d.get("player_id")),
        "deactivate_split2": lambda d: handle_deactivate_split2(d.get("player_id")),
        "manual_make_win": lambda d: handle_manual_make_result(d.get("player_id"), d.get("split_level", 0), d.get("hand_index", 0), "win"),
        "manual_make_lose": lambda d: handle_manual_make_result(d.get("player_id"), d.get("split_level", 0), d.get("hand_index", 0), "fail"),
        "manual_make_tie": lambda d: handle_manual_make_result(d.get("player_id"), d.get("split_level", 0), d.get("hand_index", 0), "tie"),
        "manual_make_surrender": lambda d: handle_manual_make_result(d.get("player_id"), d.get("split_level", 0), d.get("hand_index", 0), "surrender"),
        "manual_make_default": lambda d: handle_manual_make_result(d.get("player_id"), d.get("split_level", 0), d.get("hand_index", 0), ""),
        "handle_manual_insurance": lambda d: handle_manual_insurance(d.get("player_id")),
        "manual_start":  lambda d: handle_manual_start(),
        "previous_turn": lambda d: handle_previous_turn(),
        "change_bets": lambda d: handle_change_bets(d.get("min_bet"), d.get("max_bet")),
        "change_table": lambda d: handle_change_table(d.get("table_number")),
        "set_live_function_hand": lambda d: set_live_function_hand(d.get("player_id"), d.get("split_level", 0), d.get("hand_index", 0), d.get("value", "")),
        "set_live_function_player": lambda d: set_live_function_player(d.get("player_id"), d.get("value", "")),
        "pull_from_pull_stack": lambda d: handle_pull_from_pull_stack(),
        "double_player": lambda d: handle_double_player(d.get("player_id"), d.get("hand_index", 0)),
        "burn_card": lambda d: handle_burn_card(d.get("card")),
        "surrender_player": lambda d: handle_surrender(d.get("player_id"), d.get("hand_index", 0)),
        "no_for_player_insurence": lambda d: no_for_player(d.get("player_id"), 'insurence'),
        "no_for_player_surrender": lambda d: no_for_player(d.get("player_id"), 'surrender'),
        "no_for_player_even_money": lambda d: no_for_player(d.get("player_id"), 'even_money'),
        "yes_for_player_insurence": lambda d: yes_for_player(d.get("player_id"), 'insurence'),
        "yes_for_player_surrender": lambda d: yes_for_player(d.get("player_id"), 'surrender'),
        "yes_for_player_even_money": lambda d: yes_for_player(d.get("player_id"), 'even_money'),
        "pull_from_pull_stack_1_hand_card": lambda d: pull_from_pull_stack_1_hand_card(),
    }

    try:
        async for message in websocket:
            data = json.loads(message)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] Received: {data}")
            
            handler = action_handlers.get(data["action"])
            if handler:
                await handler(data)

    except websockets.ConnectionClosed:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] Client disconnected: {websocket.remote_address}")
    finally:
        connected_clients.remove(websocket)

async def handle_set_game_mode(mode):
    log_function_call("handle_set_game_mode", mode=mode)
    print(f"[DEBUG] Setting game mode to {mode}")
    
    # Check if we're switching between LIVE and AUTO modes
    old_mode = game_state.get("mode", "")
    if (old_mode == "live" and mode == "auto") or (old_mode == "auto" and mode == "live"):
        print(f"[DEBUG] Switching from {old_mode} to {mode} - creating new deck")
        # Create a new deck while preserving active players
        game_state["deck"] = create_deck()
        print(f"[DEBUG] New deck created with {len(game_state['deck'])} cards")
        
        # Clear all cards from players and dealer but keep their active status
        # Clear dealer cards
        game_state["dealer"]["cards"] = []
        game_state["dealer"]["total"] = 0
        game_state["dealer"]["status"] = "playing"
        game_state["dealer"]["result"] = ""
        game_state["dealer"]["live_function_hand"] = ""
        
        # Clear all player cards but preserve their active status
        for player_id, player_data in game_state["players"].items():
            # Clear main hands
            for hand in player_data["hands"]:
                hand["cards"] = []
                hand["total"] = 0
                hand["status"] = "waiting"
                hand["result"] = ""
                hand["live_function_hand"] = ""
                hand["double_status"] = ""
            
            # Clear split hands
            for hand in player_data["split1"]:
                hand["cards"] = []
                hand["total"] = 0
                hand["status"] = "waiting"
                hand["result"] = ""
                hand["live_function_hand"] = ""
                hand["double_status"] = ""
            
            for hand in player_data["split2"]:
                hand["cards"] = []
                hand["total"] = 0
                hand["status"] = "waiting"
                hand["result"] = ""
                hand["live_function_hand"] = ""
                hand["double_status"] = ""
            
            # Reset other game state but preserve active status
            player_data["split1_status"] = 0
            player_data["split2_status"] = 0
            player_data["insurence"] = 0
            player_data["surrender"] = 0
            player_data["even_money"] = 0
            player_data["live_function_player"] = ""
        
        # Reset round number and other game state
        game_state["round_number"] = 0
        game_state["current_player"] = None
        game_state["game_phase"] = "betting"
        game_state["selected_hand"] = None
        
        print(f"[DEBUG] Game state reset for mode switch - active players preserved")
    
    game_state["mode"] = mode
    await broadcast({
        "action": "game_state_update",
        "game_state": serialize_game_state(),
        "message": f"Game mode set to {mode.title()}" + (" with new deck" if (old_mode == "live" and mode == "auto") or (old_mode == "auto" and mode == "live") else "")
    })
    log_game_state()

async def handle_reshuffle():
    log_function_call("handle_reshuffle")
    game_state["deck"] = create_deck()
    await broadcast({
        "action": "deck_reshuffled",
        "deck_count": len(game_state["deck"]),
        "message": "Deck reshuffled to 6 full decks (312 cards)"
    })
    log_game_state()

async def no_for_player(player_id, action):
    """Set a player's value to -1 (for no/decline actions)"""
    if player_id and player_id in game_state["players"]:
        # Set the specific action field to -1
        game_state["players"][player_id][action] = -1
        await broadcast({
            "action": "player_no_action",
            "player_id": player_id,
            "action_type": action,
            "game_state": serialize_game_state()
        })
        # Check if all players are done
        await check_all_done()

async def check_all_done():
    """Check if all active players have made their decisions and set all_done accordingly"""
    active_players = [pid for pid, pdata in game_state["players"].items() if pdata["status"] == 1]
    
    if not active_players:
        return
    
    # Check if dealer has cards (game has started)
    if not game_state["dealer"]["cards"]:
        return
    
    all_insurance_done = True
    all_surrender_done = True
    all_even_money_done = True
    
    for player_id in active_players:
        player_data = game_state["players"][player_id]
        
        # Only check players who have main hands with cards
        if not player_data.get("hands") or not player_data["hands"][0].get("cards"):
            continue
            
        # Check insurance decisions
        if player_data.get("insurence", 0) == 0:
            # Only check even_money if insurance is 0 (not taken)
            if player_data.get("even_money", 0) == 0:
                all_insurance_done = False
                all_even_money_done = False
        
        # Check surrender decisions
        if player_data.get("surrender", 0) == 0:
            all_surrender_done = False
    # Set all_done to 1 if all decisions are made
    # For insurance scenarios (dealer has Ace), only check insurance and even_money
    # For surrender scenarios (dealer doesn't have Ace), only check surrender
    dealer_has_ace = game_state["dealer"]["cards"] and game_state["dealer"]["cards"][0][0] == 'A'
    
    if dealer_has_ace:
        # Insurance scenario - only check insurance and even_money
        if all_insurance_done and all_even_money_done:
            game_state["all_done"] = 1
            
            # Set selected_hand to first active hand that is not blackjack and not surrendered
            all_hands = get_all_player_hands()
            selected_hand = None
            
            for hand in all_hands:
                player_id = hand["player_id"]
                if player_id in game_state["players"]:
                    player = game_state["players"][player_id]
                    
                    # Check if player has surrendered
                    if player.get("surrender") == 1:
                        continue  # Skip surrendered players
                    
                    # Get the hand based on split level
                    split_level = hand["split_level"]
                    hand_index = hand["hand_index"]
                    
                    if split_level == 0:  # Main hand
                        player_hand = player["hands"][hand_index]
                    elif split_level == 1:  # Split1 hand
                        player_hand = player["split1"][hand_index]
                    elif split_level == 2:  # Split2 hand
                        player_hand = player["split2"][hand_index]
                    else:
                        continue
                    
                    # Check if hand is blackjack (21 with 2 cards)
                    if len(player_hand["cards"]) == 2 and calculate_hand_value(player_hand["cards"]) == 21:
                        continue  # Skip blackjack hands
                    
                    # Found first active hand that is not surrendered and not blackjack
                    selected_hand = hand
                    break
            
            if selected_hand:
                game_state["selected_hand"] = selected_hand
                game_state["current_player"] = selected_hand["player_id"]
            else:
                # Fallback to first active hand if no suitable hand found
                first_active_hand = get_first_active_player_hand()
                if first_active_hand:
                    game_state["selected_hand"] = first_active_hand
                    game_state["current_player"] = first_active_hand["player_id"]
                else:
                    game_state["current_player"] = None
            
            print(f"Selected hand: {selected_hand}")
            print(f"Current player: {game_state['current_player']}")

            await broadcast({
                "action": "all_done_updated",
                "all_done": 1,
                "game_state": serialize_game_state()
            })
    else:
        # Surrender scenario - only check surrender
        if all_surrender_done:
            game_state["all_done"] = 1
            
            # Set selected_hand to first active hand that is not blackjack and not surrendered
            all_hands = get_all_player_hands()
            selected_hand = None
            
            for hand in all_hands:
                player_id = hand["player_id"]
                if player_id in game_state["players"]:
                    player = game_state["players"][player_id]
                    
                    # Check if player has surrendered
                    if player.get("surrender") == 1:
                        continue  # Skip surrendered players
                    
                    # Get the hand based on split level
                    split_level = hand["split_level"]
                    hand_index = hand["hand_index"]
                    
                    if split_level == 0:  # Main hand
                        player_hand = player["hands"][hand_index]
                    elif split_level == 1:  # Split1 hand
                        player_hand = player["split1"][hand_index]
                    elif split_level == 2:  # Split2 hand
                        player_hand = player["split2"][hand_index]
                    else:
                        continue
                    
                    # Check if hand is blackjack (21 with 2 cards)
                    if len(player_hand["cards"]) == 2 and calculate_hand_value(player_hand["cards"]) == 21:
                        continue  # Skip blackjack hands
                    
                    # Found first active hand that is not surrendered and not blackjack
                    selected_hand = hand
                    break
            
            if selected_hand:
                game_state["selected_hand"] = selected_hand
                game_state["current_player"] = selected_hand["player_id"]
            else:
                # Fallback to dealer if no suitable hand found
                game_state["current_player"] = "dealer"
                game_state["selected_hand"] = {
                        "player_id": "dealer",
                        "hand_index": 0,
                        "split_level": 0
                }
            
            print(f"Selected hand: {selected_hand}")
            print(f"Current player: {game_state['current_player']}")

            await broadcast({
                "action": "all_done_updated",
                "all_done": 1,
                "game_state": serialize_game_state()
            })

async def yes_for_player(player_id, action):
    """Set a player's value to 1 (for yes/accept actions)"""
    if player_id and player_id in game_state["players"]:
        # Set the specific action field to 1
        game_state["players"][player_id][action] = 1
        await broadcast({
            "action": "player_yes_action",
            "player_id": player_id,
            "action_type": action,
            "game_state": serialize_game_state()
        })
        # Check if all players are done
        await check_all_done()

async def handle_activate_player(player_id=None):
    log_function_call("handle_activate_player", player_id=player_id)
    # Count active players (status = 1)
    active_players = get_active_players()
    
    if len(active_players) >= game_state["max_players"]:
        await broadcast({"action": "error", "message": "Maximum players reached"})
        return
    
    if player_id and player_id in game_state["players"]:
        # Activate specific player if provided and exists
        if game_state["players"][player_id]["status"] == 0:
            game_state["players"][player_id].update({
                "status": 1,
                "hands": [{"cards": [], "total": 0, "status": "playing", "result": "", "live_function_hand": "", "double_status": ""}]
            })
            
            # If this is the first active player, set them as current player
            if len(active_players) == 0:
                game_state["current_player"] = player_id
                game_state["game_phase"] = "waiting"
            
            # Set this player as selected when activating
            game_state["selected_hand"] = get_first_active_player_hand()
            
            await broadcast({
                "action": "player_activated",
                "player_id": player_id,
                "message": f"Player {player_id} has been activated",
                "current_player": game_state["current_player"],
                "selected_hand": game_state["selected_hand"],
                "game_state": serialize_game_state()
            })
        else:
            await broadcast({
                "action": "error",
                "message": f"Player {player_id} is already active"
            })
    else:
        await broadcast({
            "action": "error",
            "message": f"Invalid player ID: {player_id}"
        })
    log_game_state()

async def handle_remove_player(player_id):
    log_function_call("handle_remove_player", player_id=player_id)
    if not player_id or player_id not in game_state["players"]:
        await broadcast({
            "action": "error",
            "message": f"Invalid player ID: {player_id}"
        })
        return
    
    if game_state["players"][player_id]["status"] == 0:
        await broadcast({
            "action": "error",
            "message": f"Player {player_id} is already inactive"
        })
        return
    
    # Reset player state
    game_state["players"][player_id].update({
        "status": 0,
        "hands": [{"cards": [], "total": 0, "status": "playing", "result": "", "live_function_hand": "", "double_status": ""}]
    })
    
    # If removing current player, update to next active player
    if game_state["current_player"] == player_id:
        active_players = get_active_players()
        if active_players:
            game_state["current_player"] = active_players[0]
        else:
            game_state["current_player"] = None
            game_state["game_phase"] = "waiting"
    
    # Clear selected hand if it was the removed player
    if game_state["selected_hand"] and game_state["selected_hand"]["player_id"] == player_id:
        game_state["selected_hand"] = get_first_active_player_hand()
    
    # Broadcast the update to all clients
    await broadcast({
        "action": "player_removed",
        "player_id": player_id,
        "message": f"Player {player_id} has been deactivated",
        "current_player": game_state["current_player"],
        "selected_hand": game_state["selected_hand"],
        "game_state": serialize_game_state()
    })
    log_game_state()

async def handle_hit_player(player_id, hand_index=0, card=None):
    """Add a card to a player's hand or the dealer's hand"""
    log_function_call("handle_hit_player", player_id=player_id, hand_index=hand_index, card=card)
    print("\n=== HANDLE HIT PLAYER STARTED ===")
    print(f"Input parameters - player_id: {player_id}, hand_index: {hand_index}, card: {card}")
    
    try:
        # Block hits after the game has been evaluated
        if game_state.get("evaluate_game"):
            print("[DEBUG] hit_player blocked: game already over")
            await broadcast({
                "action": "error",
                "message": "game already over",
                "game_state": serialize_game_state()
            })
            return

        total_cards_in_play = count_total_cards_in_play()
        print(f"[DEBUG] Mode: {game_state['mode']}, Total cards in play: {total_cards_in_play}")
        
        # Check if we should burn the card (no current player or selected hand)
        if (game_state["selected_hand"] is None) and card:
            print(f"[DEBUG] Burning card {card} - no current player or selected hand")
            if not (len(card) >= 2 and card[-1] in ['S', 'D', 'C', 'H']):
                await broadcast({"action": "error", "message": "Invalid card format"})
                return
            if card in game_state["deck"]:
                game_state["deck"].remove(card)
                print(f"[handle_hit_player] Burned card: {card}")
                
                # Save action to history
                await save_action_history("burn_card", {"card": card})
                
                await broadcast({
                    "action": "card_burned",
                    "card": card,
                    "message": f"Card {card} has been burned",
                    "game_state": serialize_game_state()
                })
                log_game_state()
                return
            else:
                await broadcast({"action": "error", "message": "Card not available in deck"})
                return
        
        if game_state["mode"] == "live" and card is None:
            print("[ERROR] No card provided in live mode. Please select or rescan the card.")
            await broadcast({
                "action": "error",
                "message": "Please select or rescan the card."
            })
            return
        if game_state["mode"] == "live" and total_cards_in_play == 0:
            print("[DEBUG] Calling handle_live_start()")
            print(card)
            await handle_live_start()
        else:
            print("[DEBUG] Not calling handle_live_start()")
        if ((game_state["mode"] == "live" and game_state["round_number"] == 0) or (game_state["mode"] == "auto" and game_state["round_number"] == 0) or game_state["round_number"] == 1):
            game_state["next_manual_counter"] = 1
            if player_id == "dealer":
                hand = game_state["dealer"]
                # If a specific card is provided
                if card:
                    if not (len(card) >= 2 and card[-1] in ['S', 'D', 'C', 'H']):
                        await broadcast({"action": "error", "message": "Invalid card format"})
                        return
                    if card in game_state["deck"]:
                        game_state["deck"].remove(card)
                    else:
                        # Card not in deck - show error
                        rank = card[0] if len(card) > 0 else "?"
                        suit = card[1] if len(card) > 1 else "?"
                        suit_name = {"S": "Spades", "D": "Diamonds", "C": "Clubs", "H": "Hearts"}.get(suit, suit)
                        print(f"[ERROR] Requested dealer card {card} not available in deck")
                        await broadcast({
                            "action": "error",
                            "message": f"Card {card} ({rank} of {suit_name}) is not available in deck. All {rank} of {suit_name} cards may have been used.",
                            "game_state": serialize_game_state()
                        })
                        return
                else:
                    if not game_state["deck"]:
                        await broadcast({"action": "error", "message": "Deck is empty"})
                        return
                    card = game_state["deck"].pop()

                hand["cards"].append(card)
                hand["total"] = calculate_hand_value(hand["cards"])
                if game_state["round_number"] == 0:
                    game_state["manual_distribution_count"] = game_state["manual_distribution_count"] + 1

                if is_bust(hand["cards"]):
                    hand["status"] = "bust"
                    hand["result"] = "fail"
                elif is_blackjack(hand["cards"]):
                    hand["status"] = "blackjack"
                    hand["result"] = "win"
                else:
                    hand["status"] = "playing"
                
                await save_action_history("hit_dealer", {"card": card})
                await broadcast({
                    "action": "dealer_hit",
                    "card": card,
                    "game_state": serialize_game_state()
                })
                print("=== HANDLE HIT DEALER COMPLETED ===")
                if game_state["game_phase"] == "dealer" and game_state["round_number"] == 0 and game_state["mode"] == "live":
                    # Dealer should auto-advance after 1 card in round 0, live mode
                    print("auto_advance (dealer)")
                    hand_ref = game_state["dealer"]
                    if hand_ref and len(hand_ref["cards"]) >= 1 and game_state["round_number"] == 0:
                        print(f"[DEBUG] Dealer has 1 card - progressing to first player for second round")
                        # Move to first active player
                        active_players = [pid for pid, pdata in game_state["players"].items() if pdata["status"] == 1]
                        if active_players:
                            first_player = active_players[0]
                            game_state["current_player"] = first_player
                            game_state["game_phase"] = "playing"
                            game_state["selected_hand"] = {
                                "player_id": first_player,
                                "hand_index": 0,
                                "split_level": 0
                            }
                            game_state["manual_distribution_count"] = 0
                            print(f"[DEBUG] Moved from dealer to {first_player}")
                            
                            await broadcast({
                                "action": "turn_updated",
                                "current_player": game_state["current_player"],
                                "selected_hand": game_state["selected_hand"],
                                "game_state": serialize_game_state()
                            })
                log_game_state()
                return

            # Validate player exists
            if player_id not in game_state["players"]:
                print(f"Error: Invalid player ID {player_id}")
                await broadcast({
                    "action": "error",
                    "message": f"Invalid player ID: {player_id}"
                })
                return
            
            player = game_state["players"][player_id]
            print(f"Player {player_id} current state:", player)
            
            if player["status"] != 1:
                print(f"Error: Player {player_id} is not active")
                await broadcast({
                    "action": "error",
                    "message": f"Player {player_id} is not active"
                })
                return
            
            hand = None
            split_level = 0
            
            if game_state["selected_hand"] and game_state["selected_hand"]["player_id"] == player_id:
                split_level = game_state["selected_hand"]["split_level"]
                if split_level == 1:
                    if hand_index >= len(player["split1"]):
                        await broadcast({"action": "error", "message": "Invalid hand index"})
                        return
                    hand = player["split1"][hand_index]
                elif split_level == 2:
                    if hand_index >= len(player["split2"]):
                        await broadcast({"action": "error", "message": "Invalid hand index"})
                        return
                    hand = player["split2"][hand_index]
                else:
                    if hand_index >= len(player["hands"]):
                        await broadcast({"action": "error", "message": "Invalid hand index"})
                        return
                    hand = player["hands"][hand_index]
            else:
                if hand_index >= len(player["hands"]):
                    await broadcast({"action": "error", "message": "Invalid hand index"})
                    return
                hand = player["hands"][hand_index]
            
            print(f"Current hand before hit:", hand)
            
            # Check if we should prevent adding card (already at limit in round 0, live mode)
            if game_state["mode"] == "live" and game_state["round_number"] == 0 and player_id != "dealer":
                dealer_has_card = len(game_state["dealer"]["cards"]) > 0
                current_card_count = len(hand["cards"])
                expected_count = 1 if not dealer_has_card else 2
                
                if current_card_count >= expected_count:
                    print(f"[WARNING] Player {player_id} already has {current_card_count} cards (expected {expected_count}). Rejecting card.")
                    await broadcast({
                        "action": "error",
                        "message": f"Player {player_id} already has {current_card_count} cards. Card rejected.",
                        "game_state": serialize_game_state()
                    })
                    return
            
            if card:
                print(f"Using provided card: {card}")
                if not (len(card) >= 2 and card[-1] in ['S', 'D', 'C', 'H']):
                    print(f"Error: Invalid card format {card}")
                    await broadcast({
                        "action": "error",
                        "message": "Invalid card format"
                    })
                    return
                if card in game_state["deck"]:
                    game_state["deck"].remove(card)
                else:
                    # Card not in deck - show error
                    rank = card[0] if len(card) > 0 else "?"
                    suit = card[1] if len(card) > 1 else "?"
                    suit_name = {"S": "Spades", "D": "Diamonds", "C": "Clubs", "H": "Hearts"}.get(suit, suit)
                    print(f"[ERROR] Requested card {card} not available in deck")
                    await broadcast({
                        "action": "error",
                        "message": f"Card {card} ({rank} of {suit_name}) is not available in deck. All {rank} of {suit_name} cards may have been used.",
                        "game_state": serialize_game_state()
                    })
                    return
            else:
                if not game_state["deck"]:
                    print("Error: Deck is empty")
                    await broadcast({
                        "action": "error",
                        "message": "Deck is empty"
                    })
                    return
                card = game_state["deck"].pop()
                print(f"Drew random card: {card}")
            hand["cards"].append(card)
            print(f"Cards after adding: {hand['cards']}")
            hand["total"] = calculate_hand_value(hand["cards"])
            if game_state["round_number"] == 0:
                game_state["manual_distribution_count"] = game_state["manual_distribution_count"] + 1
            print(f"New total: {hand['total']}")
            
            if hand["status"] == "waiting":
                hand["status"] = "playing"
            
            # Check for split Ace hands with 2 cards - auto-advance turn
            if ((player["split1_status"] == 1 or player["split2_status"] == 1) and 
                len(hand["cards"]) > 0 and hand["cards"][0][:-1] == 'A' and 
                len(hand["cards"]) == 2 and hand["total"] != 21):
                print(f"[DEBUG] Auto-advancing turn for {player_id} (split Ace hand with 2 cards)")
                await handle_next_turn()
            
            if is_bust(hand["cards"]):
                hand["status"] = "bust"
                hand["result"] = "fail"
                if game_state["mode"] == "live":
                    set_live_function_hand(player_id, split_level, hand_index, "bust")
                print(f"Hand busted with total {hand['total']}")
                await handle_next_turn()
            elif is_blackjack(hand["cards"]):
                if game_state["mode"] == "live" or game_state["mode"] == "auto":
                    # Check if this is a split hand (any split, not just Ace)
                    if is_split_hand(player, split_level):
                        set_live_function_hand(player_id, split_level, hand_index, "21")
                    else:
                        set_live_function_hand(player_id, split_level, hand_index, "blackjack")
                        hand["status"] = "blackjack"
                        hand["result"] = "win"
                        player["surrender"] = -1
                print(f"Blackjack!")
                if game_state["round_number"] == 1:
                    await handle_next_turn()
            elif hand["total"] == 21:
                if game_state["mode"] == "live":
                    set_live_function_hand(player_id, split_level, hand_index, "21")
                await handle_next_turn()
            
            print("Saving action to history...")
            history_data = {
                "player_id": player_id,
                "hand_index": hand_index,
                "split_level": split_level,
                "card": card
            }
            print(f"History data: {history_data}")
            await save_action_history("hit_player", history_data)
            print("Action saved to history")
            
            print("Broadcasting updated game state...")
            broadcast_data = {
                "action": "player_hit",
                "player_id": player_id,
                "hand_index": hand_index,
                "split_level": split_level,
                "card": card,
                "game_state": serialize_game_state()
            }
            print(f"Broadcast data: {broadcast_data}")
            await broadcast(broadcast_data)
            print("Game state broadcasted")
            
            print("\n=== HANDLE HIT PLAYER COMPLETED ===")
            print("Updated player state:", game_state["players"][player_id])
            log_game_state()

            # If all players are bust or surrendered, mark evaluation complete
            try:
                if all_players_bust_or_surrender():
                    game_state["evaluate_game"] = True
                    await broadcast({
                        "action": "game_evaluated",
                        "game_state": serialize_game_state()
                    })
            except Exception as _e:
                print(f"[WARN] all_players_bust_or_surrender check failed: {_e}")

            # Check if live_function_hand was "Hit" and clear it (so buttons reappear)
            # This applies to all modes now to support visual feedback
            if True:
                # Get the current live_function_hand value before it was reset
                current_live_function_hand = ""
              
                player = game_state["players"][player_id]
                if split_level == 1:
                    current_live_function_hand = player["split1"][hand_index]["live_function_hand"]
                    if current_live_function_hand == "Hit":
                        player["split1"][hand_index]["live_function_hand"] = ""
                        print("woooooooo1")
                        # Broadcast the updated game state to all clients
                        await broadcast({
                            "action": "live_function_hand_updated",
                            "player_id": player_id,
                            "split_level": split_level,
                            "hand_index": hand_index,
                            "value": "",
                            "game_state": serialize_game_state()
                        })
                    # Add any additional logic needed when live_function_hand was "Hit"

                elif split_level == 2:
                    current_live_function_hand = player["split2"][hand_index]["live_function_hand"]
                    if current_live_function_hand == "Hit":
                        player["split2"][hand_index]["live_function_hand"] = ""
                        print("woooooooo2")
                        # Broadcast the updated game state to all clients
                        await broadcast({
                            "action": "live_function_hand_updated",
                            "player_id": player_id,
                            "split_level": split_level,
                            "hand_index": hand_index,
                            "value": "",
                            "game_state": serialize_game_state()
                        })

                else:
                    current_live_function_hand = player["hands"][hand_index]["live_function_hand"]
                    if current_live_function_hand == "Hit":
                        player["hands"][hand_index]["live_function_hand"] = ""
                        print("woooooooo3")
                        # Broadcast the updated game state to all clients
                        await broadcast({
                            "action": "live_function_hand_updated",
                            "player_id": player_id,
                            "split_level": split_level,
                            "hand_index": hand_index,
                            "value": "",
                            "game_state": serialize_game_state()
                        })
                
                # If the live_function_hand was "Hit", perform additional logic here

            # Direct progression to next player in live mode, round 0
            if game_state["mode"] == "live" and game_state["round_number"] == 0 and player_id != "dealer":
                dealer_has_card = len(game_state["dealer"]["cards"]) > 0
                hand_card_count = len(hand["cards"])
                expected_count = 1 if not dealer_has_card else 2
                
                if hand_card_count >= expected_count:
                    print(f"[DEBUG] Player {player_id} has {hand_card_count} cards (expected {expected_count}). Progressing to next player...")
                    
                    # Get all active player hands
                    all_hands = get_all_player_hands()
                    current_selected = game_state.get("selected_hand")
                    
                    # Find current hand index
                    current_index = -1
                    if current_selected:
                        current_index = next(
                            (i for i, h in enumerate(all_hands)
                            if h["player_id"] == current_selected["player_id"]
                            and h["hand_index"] == current_selected["hand_index"]
                            and h["split_level"] == current_selected["split_level"]),
                            -1
                        )
                    
                    # Find next hand
                    next_hand = None
                    active_players = [pid for pid, pdata in game_state["players"].items() if pdata["status"] == 1]
                    
                    if current_index >= 0 and current_index < len(all_hands) - 1:
                        # Move to next hand in list
                        next_hand = all_hands[current_index + 1]
                    elif not dealer_has_card:
                        # First round: check if all players have 1 card, then go to dealer
                        all_have_1 = all(len(game_state["players"][pid]["hands"][0]["cards"]) >= 1 for pid in active_players)
                        if all_have_1:
                            # Move to dealer
                            game_state["current_player"] = "dealer"
                            game_state["game_phase"] = "dealer"
                            game_state["selected_hand"] = {"player_id": "dealer", "hand_index": 0, "split_level": 0}
                            game_state["manual_distribution_count"] = 0
                            print(f"[DEBUG] All players have 1 card - moving to dealer")
                            
                            await broadcast({
                                "action": "turn_updated",
                                "current_player": game_state["current_player"],
                                "selected_hand": game_state["selected_hand"],
                                "game_state": serialize_game_state()
                            })
                    elif dealer_has_card:
                        # Second round: check if all players have 2 cards, then distribution is complete
                        all_have_2 = all(len(game_state["players"][pid]["hands"][0]["cards"]) >= 2 for pid in active_players)
                        if all_have_2:
                            # Distribution complete - set round_number to 1
                            game_state["round_number"] = 1
                            print(f"[DEBUG] All players have 2 cards - distribution complete, round_number set to 1")
                            
                            await broadcast({
                                "action": "update_game_state",
                                "game_state": serialize_game_state()
                            })
                    
                    if next_hand:
                        # Move to next player
                        game_state["current_player"] = next_hand["player_id"]
                        game_state["selected_hand"] = {
                            "player_id": next_hand["player_id"],
                            "hand_index": next_hand["hand_index"],
                            "split_level": next_hand["split_level"]
                        }
                        game_state["manual_distribution_count"] = 0  # Reset for next player
                        print(f"[DEBUG] Progressed from {player_id} to {next_hand['player_id']}")
                        
                        await broadcast({
                            "action": "turn_updated",
                            "current_player": game_state["current_player"],
                            "selected_hand": game_state["selected_hand"],
                            "game_state": serialize_game_state()
                        })
            
            # Check if double_status is "1" and mode is "live", then call handle_next_turn
            if player_id in game_state["players"] and player_id != "dealer":
                player = game_state["players"][player_id]
                double_status = ""
                if split_level == 1:
                    double_status = player["split1"][hand_index]["double_status"]
                elif split_level == 2:
                    double_status = player["split2"][hand_index]["double_status"]
                else:
                    double_status = player["hands"][hand_index]["double_status"]
                
                if double_status == "1" and game_state["mode"] == "live":
                    # Avoid double-advancing if we've already advanced due to bust/blackjack/21
                    if hand.get("status") not in ["bust", "blackjack"] and hand.get("total") != 21:
                        print(f"[DEBUG] Auto-advancing turn for {player_id} (double down, live mode)")
                        await handle_next_turn()                    

                
    except Exception as e:
        print(f"Error in handle_hit_player: {str(e)}")
        import traceback
        print("Traceback:", traceback.format_exc())
        await broadcast({
            "action": "error",
            "message": f"Error adding card: {str(e)}"
        })

def log_game_state():
    print("hi")

def get_last_active_hand():
    """Get the last possible player hand in the game (excluding dealer)"""
    last_hand = None
    for player_id, player_data in game_state["players"].items():
        if player_data["status"] == 1:
            # Main hand
            last_hand = {
                "player_id": player_id,
                "hand_index": 0,
                "split_level": 0
            }
            # Split1
            if player_data["split1_status"] == 1:
                last_hand = {
                    "player_id": player_id,
                    "hand_index": 0,
                    "split_level": 1
                }
            # Split2
            if player_data["split2_status"] == 1:
                last_hand = {
                    "player_id": player_id,
                    "hand_index": 0,
                    "split_level": 2
                }
    return last_hand

async def handle_split_player_live(player_id):
    """Handle splitting a player's hand into two separate hands"""
    log_function_call("handle_split_player_auto", player_id=player_id)
    import copy
    # Save the current game state to previous_game_states as an action
    previous_game_states.append(copy.deepcopy(game_state))
    if len(previous_game_states) > 10:
        previous_game_states.pop(0)

    if not player_id or player_id not in game_state["players"]:
        await broadcast({"action": "error", "message": "Invalid player ID"})
        return
    
    player_data = game_state["players"][player_id]
    
    selected = game_state.get("selected_hand")
    if not selected or selected["player_id"] != player_id:
        await broadcast({"action": "error", "message": "No selected hand for this player to split"})
        return
    split_level = selected["split_level"]
    if split_level == 0:
        hand_list = player_data["hands"]
    elif split_level == 1:
        hand_list = player_data["split1"]
    elif split_level == 2:
        hand_list = player_data["split2"]
    else:
        await broadcast({"action": "error", "message": "Invalid split level"})
        return
    if len(hand_list) == 0 or len(hand_list[0]["cards"]) != 2:
        await broadcast({"action": "error", "message": "Cannot split - no valid hand found"})
        return
    active_hand = hand_list[0]

    # Validate conditions for splitting
    if not can_split(active_hand["cards"]):
        await broadcast({"action": "error", "message": "Cannot split - cards must be of same rank"})
        return
    
    # Save action to history before modifying state
    await save_action_history("split_player", {
        "player_id": player_id,
        "original_hand": copy.deepcopy(active_hand),
        "split_level": split_level
    })

    # Split the cards
    card1, card2 = active_hand["cards"]

    # Update the original hand with first card
    active_hand["cards"] = [card1]
    active_hand["total"] = calculate_hand_value([card1])
    active_hand["status"] = "playing"

    # Create new hand with second card
    new_hand = {
        "cards": [card2],
        "total": calculate_hand_value([card2]),
        "status": "playing",
        "result": "",
        "live_function_hand": "",
        "double_status": ""
    }

    # Add new hand to the appropriate split level
    if split_level == 0:  # Splitting main hand
        if player_data["split1_status"] == 0:
            player_data["split1"] = [new_hand]
            player_data["split1_status"] = 1
            game_state["split_call_live_previous_counter"] = 1
        elif player_data["split2_status"] == 0:
            player_data["split2"] = [new_hand]
            player_data["split2_status"] = 1
            game_state["split_call_live_previous_counter"] = 2
        else:
            await broadcast({"action": "error", "message": "Maximum splits reached"})
            return
    elif split_level == 1:  # Splitting split1
        if player_data["split2_status"] == 0:
            player_data["split2"] = [new_hand]
            player_data["split2_status"] = 1
            game_state["split_call_live_previous_counter"] = 2
        else:
            await broadcast({"action": "error", "message": "Maximum splits reached"})
            return
    elif split_level == 2:  # Splitting split2
        await broadcast({"action": "error", "message": "Maximum splits reached"})
        return
    
    # If the original hand was blackjack, it's no longer blackjack after split
    if active_hand.get("blackjack", False):
        active_hand["blackjack"] = False
        active_hand["status"] = "playing"
    
    # Remove dealing new cards to both split hands
    # for hand in [active_hand, new_hand]:
    #     if len(game_state["deck"]) > 0:
    #         new_card = game_state["deck"].pop()
    #         hand["cards"].append(new_card)
    #         hand["total"] = calculate_hand_value(hand["cards"])
    
    # Reset live_function_hand for the selected hand after split completion
    if split_level == 0:
        # Main hand
        if len(player_data["hands"]) > 0:
            player_data["hands"][0]["live_function_hand"] = ""
    elif split_level == 1:
        # Split1 hand
        if player_data["split1"] and len(player_data["split1"]) > 0:
            player_data["split1"][0]["live_function_hand"] = ""
    elif split_level == 2:
        # Split2 hand
        if player_data["split2"] and len(player_data["split2"]) > 0:
            player_data["split2"][0]["live_function_hand"] = ""
    
    await broadcast({
        "action": "player_split",
        "player_id": player_id,
        "split_level": split_level,
        "game_state": serialize_game_state()
    })

    log_game_state()

async def handle_split_player_auto(player_id):
    """Handle splitting a player's hand into two separate hands"""
    log_function_call("handle_split_player_auto", player_id=player_id)

    if not player_id or player_id not in game_state["players"]:
        await broadcast({"action": "error", "message": "Invalid player ID"})
        return
    
    player_data = game_state["players"][player_id]
    
    selected = game_state.get("selected_hand")
    if not selected or selected["player_id"] != player_id:
        await broadcast({"action": "error", "message": "No selected hand for this player to split"})
        return
    split_level = selected["split_level"]
    if split_level == 0:
        hand_list = player_data["hands"]
    elif split_level == 1:
        hand_list = player_data["split1"]
    elif split_level == 2:
        hand_list = player_data["split2"]
    else:
        await broadcast({"action": "error", "message": "Invalid split level"})
        return
    if len(hand_list) == 0 or len(hand_list[0]["cards"]) != 2:
        await broadcast({"action": "error", "message": "Cannot split - no valid hand found"})
        return
    active_hand = hand_list[0]

    # Validate conditions for splitting
    if not can_split(active_hand["cards"]):
        await broadcast({"action": "error", "message": "Cannot split - cards must be of same rank"})
        return
    
    # Save action to history before modifying state
    await save_action_history("split_player", {
        "player_id": player_id,
        "original_hand": copy.deepcopy(active_hand),
        "split_level": split_level
    })

    # Split the cards
    # Pop two cards from the deck for the split
    if len(game_state["deck"]) < 2:
        await broadcast({"action": "error", "message": "Not enough cards in deck to split"})
        return
    card1 = game_state["deck"].pop()

    # Save the original two cards before split
    original_card1, original_card2 = active_hand["cards"]

    # Update the original hand with its original first card and card1
    active_hand["cards"] = [original_card1, card1]
    active_hand["total"] = calculate_hand_value(active_hand["cards"])
    active_hand["status"] = "playing"

    # Create new hand with its original second card and card2
    new_hand = {
        "cards": [original_card2],
        "total": calculate_hand_value([original_card2]),
        "status": "playing",
        "result": "",
        "live_function_hand": "",
        "double_status": ""
    }
    print(f"New cards: {card1}")
    # Add new hand to the appropriate split level
    if split_level == 0:  # Splitting main hand
        if player_data["split1_status"] == 0:
            player_data["split1"] = [new_hand]
            player_data["split1_status"] = 1
        elif player_data["split2_status"] == 0:
            player_data["split2"] = [new_hand]
            player_data["split2_status"] = 1
        else:
            await broadcast({"action": "error", "message": "Maximum splits reached"})
            return
    elif split_level == 1:  # Splitting split1
        if player_data["split2_status"] == 0:
            player_data["split2"] = [new_hand]
            player_data["split2_status"] = 1
        else:
            await broadcast({"action": "error", "message": "Maximum splits reached"})
            return
    elif split_level == 2:  # Splitting split2
        await broadcast({"action": "error", "message": "Maximum splits reached"})
        return
    
    # If the original hand was blackjack, it's no longer blackjack after split
    if active_hand.get("blackjack", False):
        active_hand["blackjack"] = False
        active_hand["status"] = "playing"
    
    # Remove dealing new cards to both split hands
    # for hand in [active_hand, new_hand]:
    #     if len(game_state["deck"]) > 0:
    #         new_card = game_state["deck"].pop()
    #         hand["cards"].append(new_card)
    #         hand["total"] = calculate_hand_value(hand["cards"])
    
    await broadcast({
        "action": "player_split",
        "player_id": player_id,
        "split_level": split_level,
        "game_state": serialize_game_state()
    })

    log_game_state()

async def save_round_results(results):
    """Save round results to MongoDB"""
    log_function_call("save_round_results", results=results)
    round_record = {
        "timestamp": datetime.utcnow(),
        "table_number": game_state["table_number"],
        "game_mode": game_state["mode"],
        "dealer_total": game_state["dealer"]["total"],
        "dealer_bust": is_bust(game_state["dealer"]["cards"]),
        "results": results
    }
    
    await results_collection.insert_one(round_record)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] Saved round results: {round_record}")

async def handle_reset_round():
    log_function_call("handle_reset_round")
    await save_action_history("reset_round", {})
    game_state["rounds_played_in_game"] += 1
    # Reset all players to waiting state, but do not touch the deck
    for player_data in game_state["players"].values():
        if player_data["status"] == 1:  # Only reset active players
            player_data.update({
                "hands": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
                "split1": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
                "split1_status": 0,
                "split2": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
                "split2_status": 0,
                "insurence": 0,
                "surrender": 0,
                "even_money": 0
            })

    # Reset dealer and game state (do not touch deck)
    game_state["dealer"].update({"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": ""})
    game_state.update({
        "game_phase": "waiting",
        "current_player": None,
        "selected_hand": get_first_active_player_hand(),  # Set to first active hand on round reset
        "evaluate_game": False,  # Reset evaluate_game flag
        "split_fire_state": 0,
        "split_current_pointer": 0,
        "auto_split_draw_card": 0,
        "split_call_live_previous_counter": 0,
        "next_manual_counter": 0,
        "manual_distribution_count": 0,
        "all_done": 0
    })
    game_state["manual_distribution_count"] = 0  # Reset manual distribution count

    await broadcast({"action": "round_reset", "game_state": serialize_game_state()})
    log_game_state()

async def handle_undo_last():
    """Undo the last action and restore previous game state"""
    log_function_call("handle_undo_last")
    
    if not previous_game_states:
        await broadcast({
            "action": "error", 
            "message": "No actions to undo"
        })
        return
    
    # Remove the most recent state (current state)
    previous_game_states.pop()
    if not previous_game_states:
        await broadcast({
            "action": "error", 
            "message": "No previous state to restore"
        })
        return
    # Restore the previous state
    prev_state = previous_game_states[-1]
    # Update all keys in game_state except action_history and previous_game_states
    for k in prev_state:
        if k != "action_history":
            game_state[k] = copy.deepcopy(prev_state[k])
    # Remove the last action from action_history
    if game_state["action_history"]:
        last_action = game_state["action_history"].pop()
    else:
        last_action = None
    # Broadcast the undo completion
    await broadcast({
        "action": "undo_completed",
        "undone_action": last_action["action"] if last_action else None,
        "message": f"Undid {last_action['action']} action" if last_action else "Undid last action",
        "game_state": serialize_game_state()
    })
    log_game_state()

async def handle_set_table_number(table_number):
    log_function_call("handle_set_table_number", table_number=table_number)
    if table_number:
        game_state["table_number"] = table_number
        await broadcast({"action": "table_number_set", "table_number": table_number})
    log_game_state()

async def handle_reset_game():
    log_function_call("handle_reset_game")
    await save_action_history("reset_game", {})
    game_state["rounds_played_in_game"] = 0
    # Reset all players to original state
    for player_id, player_data in game_state["players"].items():
        player_data.update({
            "hands": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split1": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split1_status": 0,
            "split2": [{"cards": [], "total": 0, "status": "waiting", "result": "", "live_function_hand": "", "double_status": ""}],
            "split2_status": 0,
            "status": 0,
            "insurence": 0,
            "surrender": 0,
            "even_money": 0
        })
    
    # Reset dealer to original state
    game_state["dealer"] = {
        "cards": [],
        "total": 0,
        "status": "waiting",
        "result": "",
        "live_function_hand": ""
    }
    
    # Reset game state to original state
    game_state.update({
        "game_phase": "waiting",
        "current_player": None,
        "selected_hand": None,  # Clear selected hand on game reset
        "deck": create_deck(),
        "action_history": [],
        # "mode": "",  # Reset to default game mode
        "table_number": 1,
        "auto_split_draw_card": 0,
        "evaluate_game": False,  # Reset evaluate_game flag
        "all_done": 0
    })
    game_state["manual_distribution_count"] = 0  # Reset manual distribution count
    
    # Broadcast the complete reset to all clients
    await broadcast({
        "action": "game_reset",
        "message": "Game has been completely reset to original state",
        "game_state": serialize_game_state()
    })
    log_game_state()

def get_active_hands():
    """Get all active hands in the game"""
    active_hands = []
    
    # Add player hands
    for player_id, player_data in game_state["players"].items():
        if player_data["status"] == 1:  # Only include active players
            # Add main hand if it's playing
            if player_data["hands"] and player_data["hands"][0]["status"] == "playing":
                active_hands.append({
                    "player_id": player_id,
                    "hand_index": 0,
                    "split_level": 0
                })
            
            # Add split1 hand if it's playing
            if player_data["split1_status"] == 1 and player_data["split1"] and player_data["split1"][0]["status"] == "playing":
                active_hands.append({
                    "player_id": player_id,
                    "hand_index": 0,
                    "split_level": 1
                })
            
            # Add split2 hand if it's playing
            if player_data["split2_status"] == 1 and player_data["split2"] and player_data["split2"][0]["status"] == "playing":
                active_hands.append({
                    "player_id": player_id,
                    "hand_index": 0,
                    "split_level": 2
                })
    
    # Add dealer's hand if it's the dealer's turn
    if game_state["dealer"]["status"] == "playing":
        active_hands.append({
            "player_id": "dealer",
            "hand_index": 0,
            "split_level": 0
        })
    
    return active_hands

def get_all_player_hands():
    """Return all possible player hands (main, split1, split2) in order, regardless of status, excluding dealer."""
    hands = []
    for player_id, player_data in game_state["players"].items():
        if player_data["status"] == 1:
            hands.append({"player_id": player_id, "hand_index": 0, "split_level": 0})
            if player_data["split1_status"] == 1:
                hands.append({"player_id": player_id, "hand_index": 0, "split_level": 1})
            if player_data["split2_status"] == 1:
                hands.append({"player_id": player_id, "hand_index": 0, "split_level": 2})
    return hands

async def handle_next_turn():
    """Handle moving to the next turn"""
    if (game_state["auto_split_draw_card"] == 1):
        game_state["auto_split_draw_card"] = 0;
    async def maybe_auto_skip_blackjack():
        player_id = game_state["current_player"]
        selected = game_state["selected_hand"]
        if player_id and player_id != "dealer" and selected:
            split_level = selected["split_level"]
            hand_index = selected["hand_index"]
            player = game_state["players"][player_id]
            if split_level == 1:
                hand = player["split1"][hand_index]
            elif split_level == 2:
                hand = player["split2"][hand_index]
            else:
                hand = player["hands"][hand_index]
            # Check for blackjack (21 with 2 cards)
            if len(hand["cards"]) == 2 and calculate_hand_value(hand["cards"]) == 21:
                print(f"Auto-skipping hand for {player_id} (blackjack)")
                await handle_next_turn()


   
    try:
        selected = game_state.get("selected_hand")
        
        if (
            selected and
            selected.get("player_id") in game_state["players"] and
            game_state["mode"] == "live" and
            game_state["players"][selected["player_id"]]["hands"][0]["cards"] and
            len(game_state["players"][selected["player_id"]]["hands"][0]["cards"]) == 2 and
            game_state["players"][selected["player_id"]]["split1_status"] == 1 and
            game_state["players"][selected["player_id"]]["split1"] and
            len(game_state["players"][selected["player_id"]]["split1"][0]["cards"]) == 1 and
            game_state["split_call_live_previous_counter"] == 1 and
            game_state["split_fire_state"] == 0
        ):
            print("yooo1")
            game_state["split_fire_state"] = 1
            game_state["split_current_pointer"] = 1

        if (
            selected and
            selected.get("player_id") in game_state["players"] and
            game_state["mode"] == "live" and
            game_state["players"][selected["player_id"]]["split1"] and
            len(game_state["players"][selected["player_id"]]["split1"][0]["cards"]) == 2 and
            game_state["players"][selected["player_id"]]["split2_status"] == 1 and
            game_state["players"][selected["player_id"]]["split2"] and
            len(game_state["players"][selected["player_id"]]["split2"][0]["cards"]) == 1 and
            game_state["split_call_live_previous_counter"] == 2 and
            game_state["split_fire_state"] == 0
        ):
            print("yooo2")
            game_state["split_fire_state"] = 1
            game_state["split_current_pointer"] = 2

        # Check if we should proceed with next_turn
        # For LIVE mode in round 0:
        #   - First round (dealer has 0 cards): allow after 1 card for players
        #   - Second round (dealer has 1 card): allow after 2 cards for players
        #   - Dealer: always allow after 1 card
        dealer_has_card = len(game_state["dealer"]["cards"]) > 0
        should_proceed = False
        
        print(f"[DEBUG handle_next_turn] round_number={game_state['round_number']}, mode={game_state['mode']}, next_manual_counter={game_state['next_manual_counter']}, current_player={game_state['current_player']}, manual_distribution_count={game_state['manual_distribution_count']}, dealer_has_card={dealer_has_card}")
        
        if game_state["round_number"] == 1:
            should_proceed = True
            print(f"[DEBUG handle_next_turn] Proceeding: round_number == 1")
        elif game_state["mode"] == "live" and game_state["round_number"] == 0 and game_state["next_manual_counter"] == 1:
            if game_state["current_player"] == "dealer":
                should_proceed = (game_state["manual_distribution_count"] >= 1)
                print(f"[DEBUG handle_next_turn] Dealer check: manual_distribution_count={game_state['manual_distribution_count']}, should_proceed={should_proceed}")
            else:
                # Player: check if first round (dealer has 0 cards) or second round (dealer has 1 card)
                if not dealer_has_card:
                    # First round: allow after 1 card (or more if we missed it)
                    should_proceed = (game_state["manual_distribution_count"] >= 1)
                    print(f"[DEBUG handle_next_turn] Player first round: manual_distribution_count={game_state['manual_distribution_count']}, should_proceed={should_proceed}")
                else:
                    # Second round: allow after 2 cards (or more if we missed it)
                    should_proceed = (game_state["manual_distribution_count"] >= 2)
                    print(f"[DEBUG handle_next_turn] Player second round: manual_distribution_count={game_state['manual_distribution_count']}, should_proceed={should_proceed}")
        elif game_state["mode"] == "auto" and game_state["round_number"] == 0 and game_state["next_manual_counter"] == 1:
            if game_state["current_player"] == "dealer":
                should_proceed = (game_state["manual_distribution_count"] == 1)
            else:
                # Auto mode: keep original logic (2 cards)
                should_proceed = (game_state["manual_distribution_count"] == 2)
        else:
            print(f"[DEBUG handle_next_turn] Condition NOT met - not proceeding")
        
        if should_proceed:
            if (game_state["mode"] == "live" and game_state["round_number"] == 0) or (game_state["mode"] == "auto" and game_state["round_number"] == 0):
                game_state["next_manual_counter"] = 0

            log_function_call("handle_next_turn")
            # Add to action_history as well
            game_state["action_history"].append({
                "action": "next_turn",
                "data": {},
                "timestamp": datetime.utcnow(),
            })
            if len(game_state["action_history"]) > 10:
                game_state["action_history"] = game_state["action_history"][-10:]
            active_players = get_active_players()
            all_hands = get_all_player_hands()
            last_hand = get_last_active_hand()
            
            print("\n=== HANDLING NEXT TURN ===")
            print(f"Active Players: {active_players}")
            print(f"All Hands: {all_hands}")
            print(f"Last Active Hand: {last_hand}")
            
            # If currently on dealer, move to first active player and their hand
            if game_state["game_phase"] == "dealer" and game_state["current_player"] == "dealer":
                print("Dealer phase complete - moving to first active player")
                # Find the first active player (excluding dealer)
                first_player = next((pid for pid in active_players if pid != "dealer"), None)
                print(f"first active player: {first_player}")
                if first_player:
                    # Check if all active players have 2 cards (second round complete)
                    all_players_have_2_cards = True
                    for pid in active_players:
                        if pid != "dealer":
                            player = game_state["players"][pid]
                            if len(player["hands"][0]["cards"]) < 2:
                                all_players_have_2_cards = False
                                break
                    
                    # Only set round_number = 1 if all players have 2 cards (distribution complete)
                    if game_state["round_number"] == 0 and all_players_have_2_cards:
                        game_state["round_number"] = 1
                        print("Round number set to 1 (all players have 2 cards)")
                    elif game_state["round_number"] == 0:
                        print("Continuing to second round of distribution (dealer has 1 card, players getting 2nd card)")
                    
                    game_state["game_phase"] = "playing"
                    game_state["current_player"] = first_player
                    game_state["selected_hand"] = {
                        "player_id": first_player,
                        "hand_index": 0,
                        "split_level": 0
                    }
                    print(f"Moved to player: {first_player}")
                    # Auto-skip if blackjack
                    await maybe_auto_skip_blackjack()
                else:
                    print("No active players found after dealer phase.")
                    game_state["game_phase"] = "waiting"
                    game_state["current_player"] = None
                    game_state["selected_hand"] = None
            else:
                # Check if current hand is the last possible hand
                current_hand = {
                    "player_id": game_state["current_player"],
                    "hand_index": game_state["selected_hand"]["hand_index"],
                    "split_level": game_state["selected_hand"]["split_level"]
                } if game_state["selected_hand"] else None
                
                if current_hand and last_hand and current_hand["player_id"] == last_hand["player_id"] and \
                current_hand["hand_index"] == last_hand["hand_index"] and \
                current_hand["split_level"] == last_hand["split_level"]:
                    print("Current hand is last active hand - moving to dealer")
                    # Check if all active players have 2 cards (distribution complete)
                    if game_state["round_number"] == 0 and game_state["mode"] == "live":
                        all_players_have_2_cards = True
                        for pid in active_players:
                            if pid != "dealer":
                                player = game_state["players"][pid]
                                if len(player["hands"][0]["cards"]) < 2:
                                    all_players_have_2_cards = False
                                    break
                        if all_players_have_2_cards:
                            game_state["round_number"] = 1
                            print("Round number set to 1 (all players have 2 cards, distribution complete)")
                    game_state["game_phase"] = "dealer"
                    game_state["current_player"] = "dealer"
                    game_state["selected_hand"] = {
                        "player_id": "dealer",
                        "hand_index": 0,
                        "split_level": 0
                    }
                else:
                    # Move to the next hand in the full list (not just active hands)
                    current_index = next(
                        (i for i, hand in enumerate(all_hands)
                        if hand["player_id"] == game_state["current_player"]
                        and hand["hand_index"] == game_state["selected_hand"]["hand_index"]
                        and hand["split_level"] == game_state["selected_hand"]["split_level"]),
                        -1
                    )
                    print(f"[DEBUG] Current index: {current_index}, Total hands: {len(all_hands)}")
                    print(f"[DEBUG] All hands: {all_hands}")
                    print(f"[DEBUG] Current player: {game_state['current_player']}, Selected hand: {game_state['selected_hand']}")
                    
                    if current_index == -1:
                        print(f"[ERROR] Current hand not found in all_hands! This should not happen.")
                        # Fallback: find first hand that's not current player
                        for hand in all_hands:
                            if hand["player_id"] != game_state["current_player"]:
                                next_hand = hand
                                print(f"[DEBUG] Fallback: Found next hand: {next_hand}")
                                break
                    else:
                        next_hand = None
                        for i in range(current_index + 1, len(all_hands)):
                            next_hand = all_hands[i]
                            print(f"[DEBUG] Found next hand at index {i}: {next_hand}")
                            break
                    if next_hand:
                        game_state["current_player"] = next_hand["player_id"]
                        game_state["selected_hand"] = {
                            "player_id": next_hand["player_id"],
                            "hand_index": next_hand["hand_index"],
                            "split_level": next_hand["split_level"]
                        }
                        print(f"Moving to next hand: Player {next_hand['player_id']}, Split Level {next_hand['split_level']}")
                        # Auto-skip if blackjack
                        await maybe_auto_skip_blackjack()
                    else:
                        # No more hands, move to dealer
                        print(f"[DEBUG] No more hands found - current_index={current_index}, all_hands length={len(all_hands)}")
                        print("No more hands found - moving to dealer phase")
                        # Check if all active players have 2 cards (distribution complete)
                        if game_state["round_number"] == 0 and game_state["mode"] == "live":
                            all_players_have_2_cards = True
                            for pid in active_players:
                                if pid != "dealer":
                                    player = game_state["players"][pid]
                                    if len(player["hands"][0]["cards"]) < 2:
                                        all_players_have_2_cards = False
                                        break
                            if all_players_have_2_cards:
                                game_state["round_number"] = 1
                                print("Round number set to 1 (all players have 2 cards, distribution complete)")
                        game_state["game_phase"] = "dealer"
                        game_state["current_player"] = "dealer"
                        game_state["selected_hand"] = {
                            "player_id": "dealer",
                            "hand_index": 0,
                            "split_level": 0
                        }
            print(f"New Current Player: {game_state['current_player']}")
            print(f"Selected Hand: {game_state['selected_hand']}")
            print(f"Game Phase: {game_state['game_phase']}")
            if (game_state['round_number'] == 0):
                game_state['manual_distribution_count'] = 0
            
            # Check if selected player has surrendered after turn update
            if game_state["selected_hand"] and game_state["selected_hand"]["player_id"] != "dealer":
                selected_player_id = game_state["selected_hand"]["player_id"]
                if selected_player_id in game_state["players"]:
                    player = game_state["players"][selected_player_id]
                    if player.get("surrender") == 1:
                        print(f"Player {selected_player_id} has surrendered, moving to next turn")
                        await handle_next_turn()
                        return  # Exit early since we're calling handle_next_turn again
            
            # Broadcast turn update
            await broadcast({
                "action": "turn_updated",
                "current_player": game_state["current_player"],
                "selected_hand": game_state["selected_hand"],
                "game_state": serialize_game_state()
            })
            print("=== TURN UPDATED ===\n")
            log_game_state()
    except Exception as e:
        print(f"Error in handle_next_turn: {str(e)}")
        await broadcast({"action": "error", "message": f"Error in next turn: {str(e)}"})

async def handle_previous_turn():
    """Handle moving to the previous turn"""
    try:
        log_function_call("handle_previous_turn")
        if game_state["split_fire_state"] == 1:
            game_state["split_fire_state"] = 0
        # Add to action_history as well
        game_state["action_history"].append({
            "action": "previous_turn",
            "data": {},
            "timestamp": datetime.utcnow(),
        })
        if len(game_state["action_history"]) > 10:
            game_state["action_history"] = game_state["action_history"][-10:]
        active_players = get_active_players()
        all_hands = get_all_player_hands()
        # If currently on dealer, move to last active hand
        if game_state["game_phase"] == "dealer" and game_state["current_player"] == "dealer":
            if all_hands:
                last_hand = all_hands[-1]
                game_state["game_phase"] = "playing"
                game_state["current_player"] = last_hand["player_id"]
                game_state["selected_hand"] = {
                    "player_id": last_hand["player_id"],
                    "hand_index": last_hand["hand_index"],
                    "split_level": last_hand["split_level"]
                }
            else:
                game_state["game_phase"] = "waiting"
                game_state["current_player"] = None
                game_state["selected_hand"] = None
        else:
            # Move to the previous hand in the full list
            current_index = next(
                (i for i, hand in enumerate(all_hands)
                 if hand["player_id"] == game_state["current_player"]
                 and hand["hand_index"] == game_state["selected_hand"]["hand_index"]
                 and hand["split_level"] == game_state["selected_hand"]["split_level"]),
                -1
            )
            prev_hand = None
            for i in range(current_index - 1, -1, -1):
                prev_hand = all_hands[i]
                break
            if prev_hand:
                game_state["current_player"] = prev_hand["player_id"]
                game_state["selected_hand"] = {
                    "player_id": prev_hand["player_id"],
                    "hand_index": prev_hand["hand_index"],
                    "split_level": prev_hand["split_level"]
                }
                game_state["game_phase"] = "playing"
            else:
                # No previous hand, move to dealer
                game_state["game_phase"] = "dealer"
                game_state["current_player"] = "dealer"
                game_state["selected_hand"] = {
                    "player_id": "dealer",
                    "hand_index": 0,
                    "split_level": 0
                }
        # Broadcast turn update
        await broadcast({
            "action": "turn_updated",
            "current_player": game_state["current_player"],
            "selected_hand": game_state["selected_hand"],
            "game_state": serialize_game_state()
        })
        log_game_state()
    except Exception as e:
        print(f"Error in handle_previous_turn: {str(e)}")
        await broadcast({"action": "error", "message": f"Error in previous turn: {str(e)}"})

async def handle_start_game():
    """Start the game and set initial turn"""
    try:
        log_function_call("handle_start_game")
        active_players = get_active_players()
        active_hands = get_active_hands()

        print("\n=== STARTING GAME ===")

        print(f"Active Players: {active_players}")
        
        if not active_players:
            await broadcast({"action": "error", "message": "No active players"})
            return
        
        # Reset game state for new round
        game_state["round_number"] = 0
        game_state["game_phase"] = "player"
        game_state["current_player"] = active_players[0]
        game_state["selected_hand"] = {
            "player_id": active_players[0],
            "hand_index": 0,
            "split_level": 0
        }
        
        # Broadcast game start
        await broadcast({
            "action": "game_started",
            "current_player": game_state["current_player"],
            "selected_hand": game_state["selected_hand"],
            "game_state": serialize_game_state()
        })
        print("=== GAME STARTED ===\n")
        log_game_state()
    except Exception as e:
        print(f"Error in handle_start_game: {str(e)}")
        await broadcast({"action": "error", "message": f"Error starting game: {str(e)}"})


async def handle_manual_start():
    """Start the game in manual mode"""
    log_function_call("handle_manual_start")
    
    print("\n=== STARTING MANUAL GAME ===")
    # Set game mode to manual
    game_state["mode"] = "manual"
    await broadcast({
        "action": "manual_mode_started",
        "game_state": serialize_game_state()
    })

async def handle_live_start():
    """Start the game in live mode"""
    log_function_call("handle_live_start")
    print("\n=== STARTING LIVE GAME ===")
    # Set game mode to manual
    game_state["mode"] = "live"
    # Start serial reading task for live mode
    if ser:
        asyncio.create_task(read_from_serial())
    await handle_start_game()  # Call handle_start_game at the start

def get_active_players():
    """Get list of active player IDs"""
    active_players = [pid for pid, pdata in game_state["players"].items() if pdata["status"] == 1]
    # Add dealer at the end
    active_players.append("dealer")
    return active_players

def should_start_new_round():
    """Check if conditions are met to start a new round"""
    # Check if any player wants to continue
    active_players = get_active_players()
    if not active_players:
        return False
        
    # Check if all players have completed their hands
    for player_id in active_players:
        player_data = game_state["players"][player_id]
        if any(hand["status"] == "playing" for hand in player_data["hands"]):
            return False
            
    # Check if dealer needs to play
    if game_state["dealer"]["status"] not in ["standing", "bust"]:
        return False
        
    return True

async def handle_distribute_cards_auto():
    await handle_start_game()  # Call handle_start_game at the start
    game_state["mode"] = "auto"  # Set mode to auto
    # Check if all player hands and dealer hand are empty
    all_empty = True
    # Check dealer
    if game_state["dealer"]["cards"]:
        all_empty = False
    # Check all players
    for player_data in game_state["players"].values():
        if player_data["hands"][0]["cards"]:
            all_empty = False
        if player_data["split1"][0]["cards"]:
            all_empty = False
        if player_data["split2"][0]["cards"]:
            all_empty = False
    if all_empty:
        print("no cards assigned")
        # First round: Give 1 card to each active player
        for player_id, player_data in game_state["players"].items():
            if player_data["status"] == 1:
                await handle_hit_player(player_id, 0)
                await asyncio.sleep(0.4)
        
        # Give 1 card to dealer, then advance turn (preserves original flow)
        await handle_hit_player("dealer", 0)
        await handle_next_turn()
        await asyncio.sleep(0.4)
        
        # Second round: Give 2nd card to each active player (one by one with delay)
        for player_id, player_data in game_state["players"].items():
            if player_data["status"] == 1:
                await handle_hit_player(player_id, 0)
                await asyncio.sleep(0.4)
        await handle_next_turn()
        await asyncio.sleep(0.4)

        # Set round_number to 1 so insurance/surrender buttons can appear
        game_state["round_number"] = 1
        print("Round number set to 1 after card distribution")

        await broadcast({
            "action": "update_game_state",
            "game_state": serialize_game_state()
        })
    else:
        print("cards exist")

async def handle_dealer_value_less_then_17():
    """Keep hitting dealer until dealer's total is >= 17.
    Only treat soft 17 as a hit when it's exactly a two-card A+6 hand.
    Do not hit on 17 when dealer has more than two cards.
    """
    print('handle_dealer_value_less_then_17()')
    already_over = 0
    # Continue only if at least one player hand is still relevant
    for player in game_state["players"].values():
        if (player["status"] == 1 and player["hands"][0]["status"] == "playing" and player["surrender"] != 1):
            for hand in player["hands"]:
                if hand["status"] != "bust":
                    already_over += 1
    if already_over != 0:
        while True:
            dealer_cards = game_state["dealer"]["cards"]
            dealer_total = game_state["dealer"]["total"]

            # Only two-card A+6 counts as soft 17 that requires a hit
            is_two_card_soft_17 = False
            if len(dealer_cards) == 2 and dealer_total == 17:
                ranks = [c[0] for c in dealer_cards]
                is_two_card_soft_17 = ("A" in ranks and "6" in ranks)

            should_hit = dealer_total < 17 or is_two_card_soft_17
            if not should_hit:
                break

            await handle_hit_player("dealer", 0)
            await asyncio.sleep(0.2)
        # Evaluate the game after dealer is done
        await evaluate_game()
    else:
        # If no relevant player hands remain, mark game evaluated immediately
        game_state["evaluate_game"] = True
        await broadcast({
            "action": "game_evaluated",
            "game_state": serialize_game_state()
        })

async def evaluate_game():
    """Evaluate all active hands: if dealer bust, all hands <= 21 win, >21 fail; else if hand > dealer and <= 21, win; if hand == dealer and <= 21, tie; else fail."""
    log_function_call("evaluate_game")
    
    # Set evaluate_game to True to indicate game has been evaluated
    game_state["evaluate_game"] = True
    
    dealer_total = game_state["dealer"]["total"]
    dealer_bust = dealer_total > 21
    dealer_cards_count = len(game_state["dealer"]["cards"])
    
    for player_id, player_data in game_state["players"].items():
        if player_data["status"] == 1:
            # Main hand
            hand = player_data["hands"][0]
            # Only evaluate if hand is not surrendered
            if hand.get("result") != "surrender" and player_data["even_money"] != 1:
                # Check if this is a split hand (any split is active)
                is_split_hand_main = is_split_hand(player_data, 0)
                    
                if dealer_bust:
                    if hand["total"] <= 21:
                        hand["result"] = "win"
                    else:
                        hand["result"] = "fail"
                else:
                    # Special case: both dealer and player have 21
                    if dealer_total == 21 and hand["total"] == 21:
                        player_cards_count = len(hand["cards"])
                        # For split hands, treat 21 as regular 21 (not blackjack) even with 2 cards
                        if is_split_hand_main and player_cards_count == 2:
                            # Split hand with 21: treat as regular 21, not blackjack
                            if dealer_cards_count == 2:
                                # Dealer has blackjack (2 cards), player has split 21: dealer wins
                                hand["result"] = "fail"
                            elif dealer_cards_count > 2:
                                # Dealer has regular 21 (>2 cards), player has split 21: tie
                                hand["result"] = "tie"
                            else:
                                # Default tie for 21 vs 21
                                hand["result"] = "tie"
                        elif dealer_cards_count == 2 and player_cards_count > 2:
                            # Dealer has 2 cards, player has >2 cards: dealer wins
                            hand["result"] = "fail"
                        elif dealer_cards_count == player_cards_count:
                            # Same number of cards: tie
                            hand["result"] = "tie"
                        elif player_cards_count == 2 and dealer_cards_count > 2:
                            # Player has 2 cards, dealer has >2 cards: player wins
                            hand["result"] = "win"
                        else:
                            # Default tie for 21 vs 21
                            hand["result"] = "tie"
                    elif hand["total"] > dealer_total and hand["total"] <= 21:
                        hand["result"] = "win"
                    elif hand["total"] == dealer_total and hand["total"] <= 21:
                        hand["result"] = "tie"
                    else:
                        hand["result"] = "fail"
            
            # Split1
            if player_data["split1_status"] == 1 and player_data["split1"]:
                split1_hand = player_data["split1"][0]
                # Only evaluate if hand is not surrendered
                if split1_hand.get("result") != "surrender":
                    # Check if this is a split hand (split1_status is 1)
                    is_split_hand_split1 = is_split_hand(player_data, 1)
                        
                    if dealer_bust:
                        if split1_hand["total"] <= 21:
                            split1_hand["result"] = "win"
                        else:
                            split1_hand["result"] = "fail"
                    else:
                        # Special case: both dealer and player have 21
                        if dealer_total == 21 and split1_hand["total"] == 21:
                            player_cards_count = len(split1_hand["cards"])
                            # For split hands, treat 21 as regular 21 (not blackjack) even with 2 cards
                            if is_split_hand_split1 and player_cards_count == 2:
                                # Split hand with 21: treat as regular 21, not blackjack
                                if dealer_cards_count == 2:
                                    # Dealer has blackjack (2 cards), player has split 21: dealer wins
                                    split1_hand["result"] = "fail"
                                elif dealer_cards_count > 2:
                                    # Dealer has regular 21 (>2 cards), player has split 21: tie
                                    split1_hand["result"] = "tie"
                                else:
                                    # Default tie for 21 vs 21
                                    split1_hand["result"] = "tie"
                            elif dealer_cards_count == 2 and player_cards_count > 2:
                                # Dealer has 2 cards, player has >2 cards: dealer wins
                                split1_hand["result"] = "fail"
                            elif dealer_cards_count == player_cards_count:
                                # Same number of cards: tie
                                split1_hand["result"] = "tie"
                            elif player_cards_count == 2 and dealer_cards_count > 2:
                                # Player has 2 cards, dealer has >2 cards: player wins
                                split1_hand["result"] = "win"
                            else:
                                # Default tie for 21 vs 21
                                split1_hand["result"] = "tie"
                        elif split1_hand["total"] > dealer_total and split1_hand["total"] <= 21:
                            split1_hand["result"] = "win"
                        elif split1_hand["total"] == dealer_total and split1_hand["total"] <= 21:
                            split1_hand["result"] = "tie"
                        else:
                            split1_hand["result"] = "fail"
            
            # Split2
            if player_data["split2_status"] == 1 and player_data["split2"]:
                split2_hand = player_data["split2"][0]
                # Only evaluate if hand is not surrendered
                if split2_hand.get("result") != "surrender":
                    # Check if this is a split hand (split2_status is 1)
                    is_split_hand_split2 = is_split_hand(player_data, 2)
                        
                    if dealer_bust:
                        if split2_hand["total"] <= 21:
                            split2_hand["result"] = "win"
                        else:
                            split2_hand["result"] = "fail"
                    else:
                        # Special case: both dealer and player have 21
                        if dealer_total == 21 and split2_hand["total"] == 21:
                            player_cards_count = len(split2_hand["cards"])
                            # For split hands, treat 21 as regular 21 (not blackjack) even with 2 cards
                            if is_split_hand_split2 and player_cards_count == 2:
                                # Split hand with 21: treat as regular 21, not blackjack
                                if dealer_cards_count == 2:
                                    # Dealer has blackjack (2 cards), player has split 21: dealer wins
                                    split2_hand["result"] = "fail"
                                elif dealer_cards_count > 2:
                                    # Dealer has regular 21 (>2 cards), player has split 21: tie
                                    split2_hand["result"] = "tie"
                                else:
                                    # Default tie for 21 vs 21
                                    split2_hand["result"] = "tie"
                            elif dealer_cards_count == 2 and player_cards_count > 2:
                                # Dealer has 2 cards, player has >2 cards: dealer wins
                                split2_hand["result"] = "fail"
                            elif dealer_cards_count == player_cards_count:
                                # Same number of cards: tie
                                split2_hand["result"] = "tie"
                            elif player_cards_count == 2 and dealer_cards_count > 2:
                                # Player has 2 cards, dealer has >2 cards: player wins
                                split2_hand["result"] = "win"
                            else:
                                # Default tie for 21 vs 21
                                split2_hand["result"] = "tie"
                        elif split2_hand["total"] > dealer_total and split2_hand["total"] <= 21:
                            split2_hand["result"] = "win"
                        elif split2_hand["total"] == dealer_total and split2_hand["total"] <= 21:
                            split2_hand["result"] = "tie"
                        else:
                            split2_hand["result"] = "fail"
    
    await broadcast({
        "action": "game_evaluated",
        "game_state": serialize_game_state()
    })

async def handle_insurence(player_id, hand_index=0, split_level=0):
    """Set the 'insurence' property of the specified player to 1 (no split logic)"""

    previous_game_states.append(copy.deepcopy(game_state))
    if len(previous_game_states) > 10:
        previous_game_states.pop(0)

    if player_id not in game_state["players"]:
        await broadcast({"action": "error", "message": f"Invalid player ID: {player_id}"})
        return
    
    # Insurance is only available for main hand (split_level = 0)
    if split_level != 0:
        await broadcast({"action": "error", "message": "Insurance is only available for main hand"})
        return
    
    game_state["players"][player_id]["insurence"] = 1
    
    # Clear live_function_hand so buttons reappear
    game_state["players"][player_id]["hands"][0]["live_function_hand"] = ""

    await broadcast({
        "action": "insurance_taken",
        "player_id": player_id,
        "game_state": serialize_game_state()
    })
    # Check if all players are done after insurance decision
    await check_all_done()

async def handle_activate_split1(player_id):
    """Activate split1 for a player"""
    log_function_call("handle_activate_split1", player_id=player_id)
    
    # Check if mode is manual
    if game_state["mode"] != "manual":
        await broadcast({"action": "error", "message": "This action is only available in manual mode"})
        return
    
    if not player_id or player_id not in game_state["players"]:
        await broadcast({"action": "error", "message": "Invalid player ID"})
        return
    
    player_data = game_state["players"][player_id]
    
    if player_data["split1_status"] == 1:
        await broadcast({"action": "error", "message": "Split1 is already active"})
        return
    
    # Create a new split1 hand
    player_data["split1"] = [{"cards": [], "total": 0, "status": "waiting", "result": ""}]
    player_data["split1_status"] = 1
    
    await broadcast({
        "action": "split1_activated",
        "player_id": player_id,
        "message": f"Split1 activated for {player_id}",
        "game_state": serialize_game_state()
    })
    log_game_state()

async def handle_activate_split2(player_id):
    """Activate split2 for a player"""
    log_function_call("handle_activate_split2", player_id=player_id)
    
    # Check if mode is manual
    if game_state["mode"] != "manual":
        await broadcast({"action": "error", "message": "This action is only available in manual mode"})
        return
    
    if not player_id or player_id not in game_state["players"]:
        await broadcast({"action": "error", "message": "Invalid player ID"})
        return
    
    player_data = game_state["players"][player_id]
    
    if player_data["split2_status"] == 1:
        await broadcast({"action": "error", "message": "Split2 is already active"})
        return
    
    # Create a new split2 hand
    player_data["split2"] = [{"cards": [], "total": 0, "status": "waiting", "result": ""}]
    player_data["split2_status"] = 1
    
    await broadcast({
        "action": "split2_activated",
        "player_id": player_id,
        "message": f"Split2 activated for {player_id}",
        "game_state": serialize_game_state()
    })
    log_game_state()

async def handle_deactivate_split1(player_id):
    log_function_call("handle_deactivate_split1", player_id=player_id)
    
    # Check if mode is manual
    if game_state["mode"] != "manual":
        await broadcast({"action": "error", "message": "This action is only available in manual mode"})
        return
    
    if not player_id or player_id not in game_state["players"]:
        await broadcast({"action": "error", "message": "Invalid player ID"})
        return
    player_data = game_state["players"][player_id]
    player_data["split1"] = [{"cards": [], "total": 0, "status": "waiting", "result": ""}]
    player_data["split1_status"] = 0
    await broadcast({
        "action": "split1_deactivated",
        "player_id": player_id,
        "message": f"Split1 deactivated for {player_id}",
        "game_state": serialize_game_state()
    })
    log_game_state()

async def handle_deactivate_split2(player_id):
    log_function_call("handle_deactivate_split2", player_id=player_id)
    
    # Check if mode is manual
    if game_state["mode"] != "manual":
        await broadcast({"action": "error", "message": "This action is only available in manual mode"})
        return
    
    if not player_id or player_id not in game_state["players"]:
        await broadcast({"action": "error", "message": "Invalid player ID"})
        return
    player_data = game_state["players"][player_id]
    player_data["split2"] = [{"cards": [], "total": 0, "status": "waiting", "result": ""}]
    player_data["split2_status"] = 0
    await broadcast({
        "action": "split2_deactivated",
        "player_id": player_id,
        "message": f"Split2 deactivated for {player_id}",
        "game_state": serialize_game_state()
    })
    log_game_state()

async def handle_manual_make_result(player_id, split_level, hand_index, result):
    log_function_call("handle_manual_make_result", player_id=player_id, split_level=split_level, hand_index=hand_index, result=result)
    
    # Check if mode is manual
    if game_state["mode"] != "manual":
        await broadcast({"action": "error", "message": "This action is only available in manual mode"})
        return
    
    # If player_id is not provided, get it from selected_hand
    if not player_id:
        selected_hand = game_state.get("selected_hand")
        if not selected_hand:
            await broadcast({"action": "error", "message": "No player selected"})
            return
        player_id = selected_hand["player_id"]
    
    if not player_id or player_id not in game_state["players"]:
        await broadcast({"action": "error", "message": "Invalid player ID"})
        return
    
    player_data = game_state["players"][player_id]
    hand = None
    
    if split_level == 1:
        if player_data["split1_status"] == 1:
            hand = player_data["split1"][hand_index]
        else:
            await broadcast({"action": "error", "message": "Split1 is not active for this player"})
            return
    elif split_level == 2:
        if player_data["split2_status"] == 1:
            hand = player_data["split2"][hand_index]
        else:
            await broadcast({"action": "error", "message": "Split2 is not active for this player"})
            return
    else:
        hand = player_data["hands"][hand_index]
    
    print(f"Setting hand result: {result} for player {player_id}, split_level {split_level}, hand_index {hand_index}")
    if hand is not None:
        hand["result"] = result
        await broadcast({
            "action": f"manual_make_{result}",
            "player_id": player_id,
            "split_level": split_level,
            "hand_index": hand_index,
            "result": result,
            "game_state": serialize_game_state()
        })
        log_game_state()
    else:
        await broadcast({"action": "error", "message": "Invalid hand index or split level for manual result"})

async def handle_manual_insurance(player_id):
    """Handle manual insurance for a player"""
    log_function_call("handle_manual_insurance", player_id=player_id)
    
    # Check if mode is manual
    if game_state["mode"] != "manual":
        await broadcast({"action": "error", "message": "This action is only available in manual mode"})
        return
    
    if player_id not in game_state["players"]:
        await broadcast({"action": "error", "message": f"Invalid player ID: {player_id}"})
        return
    
    player_data = game_state["players"][player_id]
    
    # Toggle insurance value: if 1, set to 0; if 0, set to 1
    current_insurance = player_data.get("insurence", 0)
    new_insurance = 0 if current_insurance == 1 else 1
    
    # Save action to history
    await save_action_history("manual_insurance", {"player_id": player_id, "insurance_value": new_insurance})
    
    player_data["insurence"] = new_insurance
    await broadcast({
        "action": "insurance_taken",
        "player_id": player_id,
        "insurance_value": new_insurance,
        "game_state": serialize_game_state()
    })
    log_game_state()

async def main():
    log_function_call("main")
    """Starts the WebSocket server."""
    # Initialize serial port for shoe reader
    global ser
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        print(f"Connected to shoe reader on {SERIAL_PORT}")
        # Start the serial reader as a background task
        serial_task = asyncio.create_task(read_from_serial())
    except serial.SerialException as e:
        print(f"Serial port error: {e}")
        logging.error(f"Failed to connect to shoe reader on {SERIAL_PORT}: {e}")
        ser = None
        # Create a dummy task that does nothing
        serial_task = asyncio.create_task(asyncio.sleep(float('inf')))

    async with websockets.serve(handle_connection, "0.0.0.0", 6790):
        ws_url = get_websocket_url(6790) or "ws://localhost:6790"
        print(f"Mini Flush WebSocket server running on {ws_url}")
        print(f"Shoe reader attempting to connect on {SERIAL_PORT}")
        try:
            await asyncio.gather(
                asyncio.Future(),  # Keep WebSocket server running
                serial_task
            )
        except KeyboardInterrupt:
            print("Shutting down server...")
            if ser and ser.is_open:
                ser.close()

# Extract card value from serial input
def extract_card_value(input_string):
    """
    Extract the card value from the input string formatted like:
    [Manual Burn Cards]<Card:{data}>
    """
    print(f"[extract_card_value] Input string: {input_string}")
    match = re.search(r"<Card:(.*?)>", input_string)
    if match:
        print(f"[extract_card_value] Match found: {match.group(1)}")
    else:
        print("[extract_card_value] No match found.")
    return match.group(1) if match else None

# Placeholder for foolproof_deal_card if not defined
async def foolproof_deal_card(card):
    """
    Deal a card from the serial reader, following the same conditions as the frontend assignCard.
    """
    logging.info(f"[foolproof_deal_card] Card received: {card}")
    print(f"[foolproof_deal_card] Card received: {card}")
    # 1. Prevent double send: not needed here, as backend is event-driven
    # 2. Dealer phase: deal to dealer
    if game_state.get('game_phase') == 'dealer':
        print("[foolproof_deal_card] Game phase is dealer. Dealing to dealer.")
        await handle_hit_player('dealer', 0, card)
        return
    # 3. Check for selected_hand and player
    selected_hand = game_state.get('selected_hand')
    print(f"[foolproof_deal_card] Selected hand: {selected_hand}")
    if not selected_hand or not selected_hand.get('player_id'):
        print("[foolproof_deal_card] No player selected for card assignment.")
        await broadcast({
            'action': 'error',
            'message': 'No player selected for card assignment.'
        })
        return
    player_id = selected_hand['player_id']
    # 4. Ensure player is active
    player = game_state['players'].get(player_id)
    print(f"[foolproof_deal_card] Player: {player_id}, Player data: {player}")
    if not player or not player.get('status'):
        print("[foolproof_deal_card] Player must be active to add cards.")
        await broadcast({
            'action': 'error',
            'message': 'Player must be active to add cards.'
        })
        return
    # 5. Assign card to the selected player/hand
    hand_index = selected_hand.get('hand_index', 0)
    print(f"[foolproof_deal_card] Assigning card {card} to player {player_id}, hand_index {hand_index}")
    await handle_hit_player(player_id, hand_index, card)

# Continuously read cards from the serial port and deal them in live mode
async def read_from_serial():
    """Continuously reads card values from the casino shoe reader and adds them to the game."""
    print("[read_from_serial] Starting to read from serial port...")
    if not ser:
        print("[read_from_serial] No serial port available, running in simulation mode")
        while True:
            await asyncio.sleep(1)  # Just sleep if no serial port
    else:
        while True:
            try:
                if ser and ser.in_waiting > 0:
                    raw_data = ser.readline().decode("utf-8").strip()
                    print(f"[read_from_serial] Raw data from serial: {raw_data}")
                    logging.info(f"Raw data from serial: {raw_data}")
                    card = extract_card_value(raw_data)
                    logging.info(f"Extracted card: {card}")
                    print(f"[read_from_serial] Extracted card: {card}")
                    if card:
                        print(f"[SHOE READER] Card read from shoe reader: {card}")
                        await foolproof_deal_card(card)
                    else:
                        logging.info("No valid card extracted from serial data.")
                        print("[read_from_serial] No valid card extracted from serial data.")
                await asyncio.sleep(0.01)  # Minimal sleep to yield control
            except Exception as e:
                print(f"[read_from_serial] Error reading from serial: {e}")
                await asyncio.sleep(1)

async def handle_change_bets(min_bet=None, max_bet=None):
    log_function_call("handle_change_bets", min_bet=min_bet, max_bet=max_bet)
    if min_bet is not None:
        game_state["min_bet"] = min_bet
    if max_bet is not None:
        game_state["max_bet"] = max_bet
    await broadcast({
        "action": "bets_changed",
        "min_bet": game_state["min_bet"],
        "max_bet": game_state["max_bet"],
        "game_state": serialize_game_state(),
        "message": f"Bets changed: min {game_state['min_bet']}, max {game_state['max_bet']}"
    })
    log_game_state()

async def handle_change_table(table_number=None):
    log_function_call("handle_change_table", table_number=table_number)
    if table_number is not None:
        game_state["table_number"] = table_number
        await broadcast({
            "action": "table_changed",
            "table_number": game_state["table_number"],
            "game_state": serialize_game_state(),
            "message": f"Table changed to {game_state['table_number']}"
        })
        log_game_state()

def count_total_cards_in_play():
    """Count the total number of cards currently held by all players (all hands, splits) and the dealer."""
    total = 0
    # Count dealer's cards
    total += len(game_state["dealer"]["cards"])
    # Count all player hands
    for player_data in game_state["players"].values():
        # Main hand
        total += len(player_data["hands"][0]["cards"])
        # Split1
        if player_data["split1_status"] == 1 and player_data["split1"]:
            total += len(player_data["split1"][0]["cards"])
        # Split2
        if player_data["split2_status"] == 1 and player_data["split2"]:
            total += len(player_data["split2"][0]["cards"])
    print(f"[count_total_cards_in_play] Total cards in play: {total}")
    return total

def all_players_bust_or_surrender() -> bool:
    """Return True if every active player's relevant hands are bust or surrendered."""
    for player_id, player_data in game_state["players"].items():
        if player_data.get("status") != 1:
            continue
        # If player-level surrender is set, they are done
        if player_data.get("surrender") == 1:
            continue

        def hand_done(hand: dict) -> bool:
            if not hand or len(hand.get("cards", [])) == 0:
                return False
            if hand.get("status") == "bust":
                return True
            if hand.get("result") == "surrender":
                return True
            return False

        main_hand = player_data["hands"][0] if player_data.get("hands") else None
        if main_hand and not hand_done(main_hand):
            return False

        if player_data.get("split1_status") == 1 and player_data.get("split1"):
            split1_hand = player_data["split1"][0]
            if split1_hand and not hand_done(split1_hand):
                return False

        if player_data.get("split2_status") == 1 and player_data.get("split2"):
            split2_hand = player_data["split2"][0]
            if split2_hand and not hand_done(split2_hand):
                return False
    return True

def get_first_active_player_hand():
    """Return the first active player (not dealer) in the format for selected_hand, skipping blackjacks and surrendered players."""
    for player_id, player_data in game_state["players"].items():
        if player_data["status"] == 1:
            # Skip if player has surrendered
            if player_data.get("surrender") == 1:
                continue
            hand = player_data["hands"][0]
            # Skip if this hand is a blackjack (21 with 2 cards)
            if len(hand["cards"]) == 2 and calculate_hand_value(hand["cards"]) == 21:
                continue
            return {
                "player_id": player_id,
                "hand_index": 0,
                "split_level": 0
            }
    return None

def set_live_function_hand(player_id, split_level=0, hand_index=0, value=""):
    """Set the live_function_hand for a given player (or dealer) and hand."""
    print(f"[set_live_function_hand] player_id={player_id}, split_level={split_level}, hand_index={hand_index}, value={value}")
    if player_id == "dealer":
        game_state["dealer"]["live_function_hand"] = value
    elif player_id in game_state["players"]:
        player = game_state["players"][player_id]
        if split_level == 1:
            player["split1"][hand_index]["live_function_hand"] = value
            # Set double_status to "1" if value is "Double"
            if value == "Double":
                player["split1"][hand_index]["double_status"] = "1"
        elif split_level == 2:
            player["split2"][hand_index]["live_function_hand"] = value
            # Set double_status to "1" if value is "Double"
            if value == "Double":
                player["split2"][hand_index]["double_status"] = "1"
        else:
            player["hands"][hand_index]["live_function_hand"] = value
            # Set double_status to "1" if value is "Double"
            if value == "Double":
                player["hands"][hand_index]["double_status"] = "1"
    else:
        print(f"[set_live_function_hand] Invalid player_id: {player_id}")
        return
    
    # Broadcast the update to all clients
    asyncio.create_task(broadcast({
        "action": "live_function_hand_updated",
        "player_id": player_id,
        "split_level": split_level,
        "hand_index": hand_index,
        "value": value,
        "game_state": serialize_game_state()
    }))


async def handle_double_player(player_id, hand_index=0):
    """Handle double down for a player - hit once and then stand"""
    log_function_call("handle_double_player", player_id=player_id, hand_index=hand_index)
    
    # Validate player exists
    if player_id not in game_state["players"]:
        await broadcast({"action": "error", "message": f"Invalid player ID: {player_id}"})
        return
    
    player = game_state["players"][player_id]
    
    # Get the selected hand to determine split level
    selected_hand = game_state.get("selected_hand")
    if not selected_hand or selected_hand["player_id"] != player_id:
        await broadcast({"action": "error", "message": "No valid hand selected for doubling"})
        return
    
    split_level = selected_hand["split_level"]
    
    # Get the specific hand
    hand = None
    if split_level == 0:
        if hand_index >= len(player["hands"]):
            await broadcast({"action": "error", "message": "Invalid hand index"})
            return
        hand = player["hands"][hand_index]
    elif split_level == 1:
        if hand_index >= len(player["split1"]):
            await broadcast({"action": "error", "message": "Invalid hand index"})
            return
        hand = player["split1"][hand_index]
    elif split_level == 2:
        if hand_index >= len(player["split2"]):
            await broadcast({"action": "error", "message": "Invalid hand index"})
            return
        hand = player["split2"][hand_index]
    else:
        await broadcast({"action": "error", "message": "Invalid split level"})
        return
    
    # Check if hand has exactly 2 cards (required for double down)
    if len(hand["cards"]) != 2:
        await broadcast({"action": "error", "message": "Can only double down with exactly 2 cards"})
        return

    # Set double_status to "1" for this hand
    hand["double_status"] = "1"
    
    # Check if the hit will result in conditions that auto-call handle_next_turn
    # We need to simulate what the hit will do to determine if we should call handle_next_turn
    # Get a card from the deck temporarily to check the result
    if not game_state["deck"]:
        await broadcast({"action": "error", "message": "Deck is empty"})
        return
    
    # Temporarily get a card to check the result
    temp_card = game_state["deck"][-1]  # Look at the top card without removing it
    temp_cards = hand["cards"] + [temp_card]
    temp_total = calculate_hand_value(temp_cards)
    
    # Check if the hit will result in auto-next-turn conditions
    will_auto_next_turn = (
        is_bust(temp_cards) or 
        (is_blackjack(temp_cards) and game_state["round_number"] == 1) or
        temp_total == 21
    )
    
    # Call handle_hit_player to add one card
    await handle_hit_player(player_id, hand_index)
    
    # Only call handle_next_turn if the hit didn't trigger auto-next-turn
    if not will_auto_next_turn:
        await handle_next_turn()

async def handle_surrender(player_id, hand_index=0):
    """Handle surrender for a player - set hand status and result to surrender"""
    log_function_call("handle_surrender", player_id=player_id, hand_index=hand_index)
    
    # Validate player exists
    if player_id not in game_state["players"]:
        await broadcast({"action": "error", "message": f"Invalid player ID: {player_id}"})
        return
    
    

    player = game_state["players"][player_id]
    
    # Surrender is only available for main hand (split_level = 0)
    split_level = 0
    
    # Get the main hand
    if hand_index >= len(player["hands"]):
        await broadcast({"action": "error", "message": "Invalid hand index"})
        return
    hand = player["hands"][hand_index]
    
    # Check if hand has exactly 2 cards (required for surrender)
    if len(hand["cards"]) != 2:
        await broadcast({"action": "error", "message": "Can only surrender with exactly 2 cards"})
        return
    
    # Check if surrender is allowed (dealer's upcard is not Ace, 10, J, Q, K)
    dealer_upcard = game_state["dealer"]["cards"][0] if game_state["dealer"]["cards"] else None
    if not dealer_upcard or dealer_upcard[:-1] in ['A']:
        await broadcast({"action": "error", "message": "Surrender not allowed against dealer's upcard"})
        return
    
    # Set player-level surrender flag
    player["surrender"] = 1
    
    # Call yes_for_player to properly handle the surrender decision
    await yes_for_player(player_id, 'surrender')
    
    # Set hand status and result to surrender
    hand["status"] = "surrender"
    hand["result"] = "surrender"
    
    # Save action to history
    await save_action_history("surrender_player", {
        "player_id": player_id,
        "hand_index": hand_index,
        "split_level": split_level
    })
    
    # Set selected_hand to next unsurrendered player before broadcasting
    first_active_hand = get_first_active_player_hand()
    if first_active_hand:
        first_player_id = first_active_hand["player_id"]
        if first_player_id in game_state["players"]:
            first_player = game_state["players"][first_player_id]
            # If first active player has surrendered, find next unsurrendered player
            if first_player.get("surrender") == 1:
                # Find next unsurrendered player
                all_hands = get_all_player_hands()
                next_unsurrendered_hand = None
                for hand in all_hands:
                    player_id = hand["player_id"]
                    if player_id in game_state["players"]:
                        player = game_state["players"][player_id]
                        if player.get("surrender") == 0:  # Not surrendered
                            next_unsurrendered_hand = hand
                            break
                
                if next_unsurrendered_hand:
                    game_state["current_player"] = next_unsurrendered_hand["player_id"]
                    game_state["selected_hand"] = next_unsurrendered_hand

                else:
                    # If no unsurrendered players found, use first active hand
                    game_state["selected_hand"] = first_active_hand
            else:
                # First active player hasn't surrendered, use first active hand
                game_state["selected_hand"] = first_active_hand
    
    # Broadcast the surrender action
    await broadcast({
        "action": "player_surrendered",
        "player_id": player_id,
        "hand_index": hand_index,
        "split_level": split_level,
        "game_state": serialize_game_state()
    })
    # If all players are bust or surrendered, mark evaluation complete
    try:
        if all_players_bust_or_surrender():
            game_state["evaluate_game"] = True
            await broadcast({
                "action": "game_evaluated",
                "game_state": serialize_game_state()
            })
    except Exception as _e:
        print(f"[WARN] all_players_bust_or_surrender check failed: {_e}")
             

async def handle_pull_from_pull_stack():
    """Pull a card from the deck and hit the current hand"""
    log_function_call("handle_pull_from_pull_stack")
    
    # Check if deck is empty
    if not game_state["deck"]:
        await broadcast({"action": "error", "message": "Deck is empty"})
        return
    
    # Pull a card from the deck
    card = game_state["deck"].pop()
    print(f"[handle_pull_from_pull_stack] Pulled card: {card}")
    
    # Get the current selected hand
    selected_hand = game_state.get("selected_hand")
    if not selected_hand:
        await broadcast({"action": "error", "message": "No hand selected"})
        return
    
    player_id = selected_hand["player_id"]
    hand_index = selected_hand["hand_index"]
    split_level = selected_hand["split_level"]
        
    # Call handle_hit_player with the pulled card
    await handle_hit_player(player_id, hand_index, card)
    
    print("yumomomo")

    await broadcast({
        "action": "pull_stack_used",
        "card": card,
        "player_id": player_id,
        "hand_index": hand_index,
        "split_level": split_level,
        "message": f"Pulled {card} from pull stack for {player_id}",
        "game_state": serialize_game_state()
    })


async def pull_from_pull_stack_1_hand_card():
    """Pull a card from the deck and hit the current hand"""
    log_function_call("pull_from_pull_stack_1_hand_card")

    selected_hand = game_state.get("selected_hand")
    print("DEBUG: game_state['mode']:", game_state.get('mode'))
    print("DEBUG: selected_hand:", selected_hand)
    if selected_hand:
        print("DEBUG: hand cards:", game_state['players'][selected_hand['player_id']]['hands'][selected_hand['hand_index']]['cards'])
    print("DEBUG: auto_split_draw_card:", game_state.get('auto_split_draw_card'))
    number_of_cards = 0  # Initialize the variable
    if (selected_hand['split_level'] == 0):
        number_of_cards = len(game_state["players"][selected_hand["player_id"]]["hands"][selected_hand["hand_index"]]["cards"])
    elif (selected_hand['split_level'] == 1):
        number_of_cards = len(game_state["players"][selected_hand["player_id"]]["split1"][selected_hand["hand_index"]]["cards"])
    elif (selected_hand['split_level'] == 2):
        number_of_cards = len(game_state["players"][selected_hand["player_id"]]["split2"][selected_hand["hand_index"]]["cards"])
    print("DEBUG: number_of_cards:", number_of_cards)
    if (number_of_cards == 1 and game_state["auto_split_draw_card"] == 0):
        game_state["auto_split_draw_card"] = 1
        print("DEBUG: auto_split_draw_card set to 1")
        await handle_pull_from_pull_stack()

def set_live_function_player(player_id, value=""):
    """Set the live_function_player for a given player."""
    print(f"[set_live_function_player] player_id={player_id}, value={value}")
    if player_id in game_state["players"]:
        game_state["players"][player_id]["live_function_player"] = value
    else:
        print(f"[set_live_function_player] Invalid player_id: {player_id}")
        return
    
    # Broadcast the update to all clients
    asyncio.create_task(broadcast({
        "action": "live_function_player_updated",
        "player_id": player_id,
        "value": value,
        "game_state": serialize_game_state()
    }))

async def handle_burn_card(card):
    """Handle burning a card - remove it from the deck without assigning it to any player"""
    log_function_call("handle_burn_card", card=card)
    
    if not card:
        await broadcast({"action": "error", "message": "No card specified for burning"})
        return
    
    # Validate card format
    if not (len(card) >= 2 and card[-1] in ['S', 'D', 'C', 'H']):
        await broadcast({"action": "error", "message": "Invalid card format"})
        return
    
    # Check if card exists in deck
    if card in game_state["deck"]:
        game_state["deck"].remove(card)
        print(f"[handle_burn_card] Burned card: {card}")
        
        # Save action to history
        await save_action_history("burn_card", {"card": card})
        
        await broadcast({
            "action": "card_burned",
            "card": card,
            "message": f"Card {card} has been burned",
            "game_state": serialize_game_state()
        })
    else:
        await broadcast({"action": "error", "message": "Card not available in deck"})
    
    log_game_state()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())