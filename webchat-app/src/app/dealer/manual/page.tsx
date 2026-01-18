"use client";
import { useState, useEffect, useRef } from "react";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { getWebSocketUrl } from "@/lib/ip-config";
import DealerNavbar from "@/components/DealerNavbar";
import BetTableModal from "@/components/BetTableModal";
import GameMenuModal from "@/components/GameMenuModal";

interface Hand {
  cards: string[];
  total: number;
  status: string;
  result?: string;
  bet?: number;
  insurence?: number;
}

interface PlayerData {
  status: number;
  hands: Hand[];
  split1: Hand[];
  split1_status: number;
  split2: Hand[];
  split2_status: number;
  insurence?: number;
  even_money?: number;
}

interface Players {
  [key: string]: PlayerData;
}

interface GameState {
  deck_count: number;
  game_mode: string;
  dealer: {
    cards: string[];
    total: number;
    status: string;
  };
  players: Players;
  game_phase: string;
  table_number: number;
  current_turn: string;
  selected_hand?: {
    player_id: string;
    hand_index: number;
    split_level: number;
  };
  current_player?: string;
  mode: string;
  round_number: number;
  evaluate_game: boolean;
  manual_distribution_count: number;
  next_manual_counter: number;
}

// Add these helper functions at the top of the file, after the interfaces
const isHandSelected = (
  gameState: GameState | null,
  playerId: string,
  handIndex: number,
  splitLevel: number
): boolean => {
  return (
    gameState?.selected_hand?.player_id === playerId &&
    gameState?.selected_hand?.hand_index === handIndex &&
    gameState?.selected_hand?.split_level === splitLevel
  );
};

const canSplit = (cards: string[]): boolean => {
  if (cards.length !== 2) return false;
  // Only compare the rank (first character)
  return cards[0][0] === cards[1][0];
};

const DebugPanel = ({ gameState }: { gameState: GameState | null }) => {
  if (!gameState) return null;

  // Group players into rows of 3
  const playerEntries = Object.entries(gameState.players);
  const playerRows = [];
  for (let i = 0; i < playerEntries.length; i += 3) {
    playerRows.push(playerEntries.slice(i, i + 3));
  }

  return <></>;
};

const GameMenu = () => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isGameStarted, setIsGameStarted] = useState(false);
  const [isRoundFinished, setIsRoundFinished] = useState(false);
  const [showNextButton, setShowNextButton] = useState(false);
  const [showPopup, setShowPopup] = useState(false);
  const [popupMessage, setPopupMessage] = useState("");
  const [isDealerSelected, setIsDealerSelected] = useState(false);
  const [selectedCard, setSelectedCard] = useState<string | null>(null);
  const [selectedSuit, setSelectedSuit] = useState<string | null>(null);
  const [insuranceState, setInsuranceState] = useState<{
    [key: string]: boolean;
  }>({});
  const [lastPlayerTotal, setLastPlayerTotal] = useState<{
    [key: string]: number;
  }>({});
  const lastDealerTotalRef = useRef(0);
  const lastPlayerTotalRef = useRef<{ [key: string]: number }>({});
  const nextTurnCalledRef = useRef<{ [key: string]: boolean }>({});
  const [waitingForServer, setWaitingForServer] = useState(false);
  const lastAutoTurnRef = useRef<{
    playerId: string | null;
    round: number;
    count: number;
  }>({ playerId: null, round: -1, count: -1 });
  const [betMenuOpen, setBetMenuOpen] = useState(false);
  const [pendingTableNumber, setPendingTableNumber] = useState(0);
  const [pendingMinBet, setPendingMinBet] = useState(0);
  const [pendingMaxBet, setPendingMaxBet] = useState(0);
  const [gameMenuOpen, setGameMenuOpen] = useState(false);
  const pathname = usePathname();

  // Set game mode helper
  const setGameMode = (mode: string) => {
    sendWebSocketMessage({
      action: "set_game_mode",
      mode,
    });
  };

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 5;
    const RECONNECT_DELAY = 3000;

    const connect = async () => {
      const wsUrl = await getWebSocketUrl(6790);
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log("Connected to server");
        setIsConnected(true);
        reconnectAttempts = 0;
        // Send set_game_mode only after connection is open
        // if (ws && ws.readyState === WebSocket.OPEN) {
        //   console.log("Sending set_game_mode to backend (onopen)");
        //   ws.send(JSON.stringify({
        //     action: 'set_game_mode',
        //     mode: 'manual'
        //   }));
        // }
      };

      ws.onclose = () => {
        console.log("Disconnected from server");
        setIsConnected(false);

        // Attempt to reconnect
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts++;
          console.log(
            `Attempting to reconnect (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`
          );
          reconnectTimeout = setTimeout(connect, RECONNECT_DELAY);
        } else {
          console.log("Max reconnection attempts reached");
          setPopupMessage("⚠️ Connection lost. Please refresh the page.");
          setShowPopup(true);
        }
      };

      // ws.onerror = error => {
      //   console.error('WebSocket error:', error)
      //   setPopupMessage('⚠️ Connection error occurred')
      //   setShowPopup(true)
      // }

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("Received:", data);

        // Update game state for all relevant actions
        if (data.game_state) {
          setGameState(data.game_state);
        }

        // Handle specific actions
        switch (data.action) {
          case "player_activated":
            // Notification removed
            break;
          case "player_removed":
            // Notification removed
            break;
          case "turn_updated":
            setIsDealerSelected(data.current_turn === "dealer");
            break;
          case "game_started":
            setIsPlaying(true);
            setIsGameStarted(true);
            setIsRoundFinished(false);
            setShowNextButton(true);
            setIsDealerSelected(data.current_turn === "dealer");
            setLastPlayerTotal({}); // Reset player totals
            lastDealerTotalRef.current = 0; // Reset dealer ref
            lastPlayerTotalRef.current = {}; // Reset player ref
            nextTurnCalledRef.current = {}; // Reset next turn called ref
            console.log(
              "Manual distribution counter reset to 0 (game started)"
            );
            break;
          case "round_reset":
            setIsPlaying(false);
            setIsGameStarted(false);
            setIsDealerSelected(false);
            setShowNextButton(false);
            setIsRoundFinished(true);
            setLastPlayerTotal({}); // Reset player totals
            lastDealerTotalRef.current = 0; // Reset dealer ref
            lastPlayerTotalRef.current = {}; // Reset player ref
            nextTurnCalledRef.current = {}; // Reset next turn called ref
            console.log("Manual distribution counter reset to 0 (round reset)");
            break;
          case "game_reset":
            // Reset all local state
            setIsPlaying(false);
            setIsGameStarted(false);
            setIsRoundFinished(false);
            setShowNextButton(false);
            setIsDealerSelected(false);
            setSelectedCard(null);
            setSelectedSuit(null);
            setLastPlayerTotal({}); // Reset player totals
            lastDealerTotalRef.current = 0; // Reset dealer ref
            lastPlayerTotalRef.current = {}; // Reset player ref
            nextTurnCalledRef.current = {}; // Reset next turn called ref
            console.log("Manual distribution counter reset to 0 (game reset)");
            setPopupMessage(data.message);
            setShowPopup(true);
            setTimeout(() => setShowPopup(false), 3000);
            break;
          case "error":
            setPopupMessage(data.message);
            setShowPopup(true);
            setTimeout(() => setShowPopup(false), 1000);
            setWaitingForServer(false); // Reset waiting state on error
            break;
          case "split1_activated":
            setPopupMessage(data.message);
            setShowPopup(true);
            setTimeout(() => setShowPopup(false), 1000);
            break;
          case "split2_activated":
            setPopupMessage(data.message);
            setShowPopup(true);
            setTimeout(() => setShowPopup(false), 1000);
            break;
          case "manual_make_win":
          case "manual_make_lose":
          case "manual_make_tie":
            setPopupMessage(`Hand set to ${data.result}`);
            setShowPopup(true);
            setTimeout(() => setShowPopup(false), 1000);
            break;
          case "player_hit":
          case "dealer_hit":
            setWaitingForServer(false);
            break;
        }
      };

      setSocket(ws);
    };

    connect();

    return () => {
      if (ws) {
        ws.close();
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, []);

  const prevIsConnectedRef = useRef(isConnected);

  useEffect(() => {
    if (
      isConnected &&
      showPopup &&
      popupMessage === "⚠️ Not connected to server"
    ) {
      const timer = setTimeout(() => setShowPopup(false), 1000);
      return () => clearTimeout(timer);
    }
  }, [isConnected, showPopup, popupMessage]);

  useEffect(() => {
    // Show connected popup only on reconnection (not initial mount)
    if (prevIsConnectedRef.current === false && isConnected) {
      setPopupMessage("✅ Connected to server");
      setShowPopup(true);
      const timer = setTimeout(() => setShowPopup(false), 1000);
      return () => clearTimeout(timer);
    }
    prevIsConnectedRef.current = isConnected;
  }, [isConnected]);

  useEffect(() => {
    // Show connected popup only on reconnection (not initial mount)
    if (prevIsConnectedRef.current === false && isConnected) {
      setPopupMessage("✅ Connected to server");
      setShowPopup(true);
      const timer = setTimeout(() => setShowPopup(false), 1000);
      return () => clearTimeout(timer);
    }
    prevIsConnectedRef.current = isConnected;
  }, [isConnected]);

  const handleMainContainerClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      // Only clear dealer selection, player selection is managed by backend
      setIsDealerSelected(false);
    }
  };

  const activatePlayer = (playerId: string) => {
    if (!socket || !isConnected) {
      setPopupMessage("⚠️ Not connected to server");
      setShowPopup(true);
      setTimeout(() => setShowPopup(false), 3000);
      return;
    }

    // Send selection to backend first
    sendWebSocketMessage({
      action: "select_player",
      player_id: playerId,
    });

    // Then activate the player
    sendWebSocketMessage({
      action: "activate_player",
      player_id: playerId,
    });
  };

  const deactivatePlayer = (playerId: string) => {
    if (!socket || !isConnected) {
      setPopupMessage("⚠️ Not connected to server");
      setShowPopup(true);
      setTimeout(() => setShowPopup(false), 3000);
      return;
    }

    // Clear selection if deactivating selected player
    if (gameState?.selected_hand?.player_id === playerId) {
      sendWebSocketMessage({
        action: "select_player",
        player_id: null,
      });
    }

    sendWebSocketMessage({
      action: "remove_player",
      player_id: playerId,
    });
  };

  const handlePlayerClick = (playerId: string) => {
    if (!socket || !isConnected) {
      setPopupMessage("⚠️ Not connected to server");
      setShowPopup(true);
      setTimeout(() => setShowPopup(false), 3000);
      return;
    }

    // Send selection to backend
    sendWebSocketMessage({
      action: "select_player",
      player_id: playerId,
    });
  };

  const startGameLoop = () => {
    if (!socket || !isConnected) {
      setPopupMessage("⚠️ Not connected to server");
      setShowPopup(true);
      setTimeout(() => setShowPopup(false), 3000);
      return;
    }

    // Check if there are any active players
    const activePlayers = getActivePlayers();
    if (activePlayers.length === 0) {
      setPopupMessage("⚠️ No active players");
      setShowPopup(true);
      setTimeout(() => setShowPopup(false), 3000);
      return;
    }

    // Send start game message
    sendWebSocketMessage({
      action: "start_game",
    });

    // Update UI states
    setIsPlaying(true);
    setIsGameStarted(true);
    setIsRoundFinished(false);
    setShowNextButton(true);
    setPopupMessage("🎮 Game started!");
    setShowPopup(true);
    setTimeout(() => setShowPopup(false), 3000);
  };

  const stopGameLoop = () => {
    if (gameState?.game_phase === "playing") {
      sendWebSocketMessage({
        action: "reset_round",
      });
    }
    setIsPlaying(false);
    setIsGameStarted(false);
    setIsDealerSelected(false);
    setShowNextButton(false);
    setIsRoundFinished(true);
    setPopupMessage("🛑 Game stopped");
    setShowPopup(true);
    setTimeout(() => setShowPopup(false), 3000);
  };

  const sendWebSocketMessage = (message: any) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      console.log("Sending message to server:", message);
      socket.send(JSON.stringify(message));
    } else {
      setPopupMessage("⚠️ Not connected to server");
      setShowPopup(true);
      setTimeout(() => setShowPopup(false), 3000);
    }
  };

  // Set game mode when component loads
  useEffect(() => {
    if (isConnected && sendWebSocketMessage && gameState?.mode !== "manual") {
      sendWebSocketMessage({
        action: "set_game_mode",
        mode: "manual",
      });
      console.log("Setting game mode to manual on component load");
    }
  }, [isConnected, sendWebSocketMessage, gameState?.mode]);

  // Add this new function to get active players
  const getActivePlayers = () => {
    if (!gameState) return [];
    return Object.entries(gameState.players)
      .filter(([_, data]) => data.status === 1)
      .map(([id]) => id);
  };

  const cardValues = [
    "A",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "T",
    "J",
    "Q",
    "K",
  ];
  const suits = [
    { symbol: "♠", value: "S", color: "text-gray-800", name: "Spades" },
    { symbol: "♦", value: "D", color: "text-red-500", name: "Diamonds" },
    { symbol: "♣", value: "C", color: "text-gray-800", name: "Clubs" },
    { symbol: "♥", value: "H", color: "text-red-500", name: "Hearts" },
  ];

  // Update the dealer total check
  const dealerTotal = gameState?.dealer?.total ?? 0;

  const handleNextTurn = () => {
    if (!socket || !isConnected) {
      setPopupMessage("⚠️ Not connected to server");
      setShowPopup(true);
      setTimeout(() => setShowPopup(false), 3000);
      return;
    }

    sendWebSocketMessage({
      action: "next_turn",
    });
  };

  const handleStandDealer = () => {
    sendWebSocketMessage({
      action: "stand_dealer",
    });
  };

  const resetGame = () => {
    if (!socket || !isConnected) {
      setPopupMessage("⚠️ Not connected to server");
      setShowPopup(true);
      setTimeout(() => setShowPopup(false), 3000);
      return;
    }

    // Reset all local state
    setIsPlaying(false);
    setIsGameStarted(false);
    setIsRoundFinished(false);
    setShowNextButton(false);
    setIsDealerSelected(false);
    setSelectedCard(null);
    setSelectedSuit(null);

    // Send reset game message to server
    sendWebSocketMessage({
      action: "reset_game",
    });

    setPopupMessage("🔄 Game has been reset");
    setShowPopup(true);
    setTimeout(() => setShowPopup(false), 3000);
  };

  const assignCard = () => {
    if (waitingForServer) return; // Prevent double send

    if (gameState?.game_phase === "dealer" && selectedCard && selectedSuit) {
      // Allow dealing card to dealer
      const cardCode = selectedCard + selectedSuit;
      setWaitingForServer(true);
      sendWebSocketMessage({
        action: "hit_dealer",
        card: cardCode,
      });
      setSelectedCard(null);
      setSelectedSuit(null);
      setIsDealerSelected(false);
      return;
    }
    if (
      !gameState?.selected_hand?.player_id ||
      !selectedCard ||
      !selectedSuit
    ) {
      setPopupMessage("⚠️ Please select player, card, and suit");
      setShowPopup(true);
      setTimeout(() => setShowPopup(false), 3000);
      return;
    }
    // Ensure player is active
    if (!gameState?.players[gameState.selected_hand.player_id]?.status) {
      setPopupMessage("⚠️ Player must be active to add cards");
      setShowPopup(true);
      setTimeout(() => setShowPopup(false), 3000);
      return;
    }
    const cardCode = selectedCard + selectedSuit;
    setWaitingForServer(true);
    // Send the hit_player action
    sendWebSocketMessage({
      action: "hit_player",
      player_id: gameState.selected_hand.player_id,
      hand_index: gameState.selected_hand.hand_index,
      card: cardCode,
    });
    setSelectedCard(null);
    setSelectedSuit(null);
  };

  const handleInsurance = (
    playerId: string,
    handIndex: number,
    splitLevel: number = 0
  ) => {
    sendWebSocketMessage({
      action: "handle_insurance",
      player_id: playerId,
      hand_index: handIndex,
      split_level: splitLevel,
    });
    setInsuranceState((prev) => ({
      ...prev,
      [`${playerId}_${handIndex}_${splitLevel}`]: true,
    }));
  };

  const clearInsuranceForHand = (
    playerId: string,
    handIndex: number,
    splitLevel: number = 0
  ) => {
    setInsuranceState((prev) => {
      const newState = { ...prev };
      delete newState[`${playerId}_${handIndex}_${splitLevel}`];
      return newState;
    });
  };

  const handleSave = () => {
    // Uncomment and implement your WebSocket calls here
    sendWebSocketMessage({
      action: "change_bets",
      min_bet: pendingMinBet,
      max_bet: pendingMaxBet,
    });
    sendWebSocketMessage({
      action: "change_table",
      table_number: pendingTableNumber,
    });

    console.log("Saving:", {
      pendingTableNumber,
      pendingMinBet,
      pendingMaxBet,
    });
  };

  // Determine current mode based on pathname
  const getCurrentMode = () => {
    if (pathname === "/dealer") return "live";
    if (pathname === "/dealer/auto") return "auto";
    if (pathname === "/dealer/manual") return "manual";
    return "manual"; // default
  };

  // const handleModeChange = (mode: string) => {
  //   // This will be called when mode changes but you don't need to do anything
  //   // since the component handles the routing internally
  //   console.log(`Mode changing to: ${mode}`)
  // }

  // Helper to get hand color class
  const getHandBoxColor = (selected: boolean, result?: string) => {
    if (selected) return "bg-yellow-300 border-2 border-yellow-500";
    if (result === "surrender")
      return "bg-blue-500 border-2 border-blue-700 text-white";
    if (result === "fail")
      return "bg-red-500 border-2 border-red-700 text-white";
    if (result === "win")
      return "bg-green-500 border-2 border-green-700 text-white";
    if (result === "tie")
      return "bg-purple-500 border-2 border-purple-700 text-white";
    return "bg-black/20";
  };

  return (
    <div className="min-h-screen bg-[#450A03] text-white px-4">
      {/* Animated Background Elements */}
      {/* <div className='fixed inset-0 overflow-hidden pointer-events-none'>
        <div className='absolute -top-4 -right-4 w-72 h-72 bg-gradient-to-br from-red-500/10 to-pink-500/10 rounded-full blur-3xl animate-pulse'></div>
        <div className='absolute -bottom-4 -left-4 w-72 h-72 bg-gradient-to-br from-red-600/10 to-red-500/10 rounded-full blur-3xl animate-pulse delay-1000'></div>
      </div> */}

      {/* Header Section */}
      {/* <div className="max-w-7xl mx-auto mb-8 relative z-10">
        <div className="bg-gradient-to-r from-red-800 to-red-700 rounded-2xl p-6 shadow-2xl border border-red-600 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <div className="w-16 h-16 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-xl flex items-center justify-center shadow-lg">
                <span className="text-2xl font-bold text-white">🎰</span>
              </div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-yellow-400 to-orange-500 bg-clip-text text-transparent">
                  Dealer Control Panel (MANUAL)
                </h1>
                <div className="flex items-center space-x-4 mt-2">
                  <p className="text-gray-200">Table FT{gameState?.table_number || 1234}</p>
                  <div
                    className={`flex items-center space-x-2 px-3 py-1 rounded-full text-sm font-medium ${isConnected
                      ? "bg-green-500/20 text-green-400 border border-green-500/30"
                      : "bg-red-500/20 text-red-400 border border-red-500/30"
                      }`}
                  >
                    <div
                      className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-400 animate-pulse" : "bg-red-400"
                        }`}
                    ></div>
                    <span className="capitalize">{isConnected ? "connected" : "disconnected"}</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => sendWebSocketMessage({ action: "manual_start" })}
                className="h-12 px-4 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white rounded-lg transition-all duration-300 transform hover:scale-105 shadow-lg flex items-center justify-center space-x-2"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Manual Start</span>
              </button>

              <button
                onClick={() => sendWebSocketMessage({ action: "reset_game" })}
                className="h-12 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white px-8 rounded-xl transition-all duration-300 transform hover:scale-105 hover:shadow-xl shadow-lg flex items-center justify-center space-x-3 font-semibold"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>New Game</span>
              </button>
            </div>
          </div>
        </div>
      </div> */}

      <DealerNavbar
        gameState={gameState}
        activatePlayer={activatePlayer}
        deactivatePlayer={deactivatePlayer}
        currentMode="manual"
        betMenuOpen={betMenuOpen}
        setBetMenuOpen={setBetMenuOpen}
        gameMenuOpen={gameMenuOpen}
        setGameMenuOpen={setGameMenuOpen}
        sendWebSocketMessage={sendWebSocketMessage}
      />

      <BetTableModal
        betMenuOpen={betMenuOpen}
        setBetMenuOpen={setBetMenuOpen}
        pendingTableNumber={pendingTableNumber}
        setPendingTableNumber={setPendingTableNumber}
        pendingMinBet={pendingMinBet}
        setPendingMinBet={setPendingMinBet}
        pendingMaxBet={pendingMaxBet}
        setPendingMaxBet={setPendingMaxBet}
        onSave={handleSave}
      />

      <GameMenuModal
        menuOpen={gameMenuOpen}
        setMenuOpen={setGameMenuOpen}
        currentMode={getCurrentMode()}
        sendWebSocketMessage={sendWebSocketMessage}
        gameState={gameState}
        setPopupMessage={setPopupMessage}
        setShowPopup={setShowPopup}
      />

      {/* <nav className='fixed top-0 left-0 right-0 h-[12vh] w-full overflow-hidden z-50 shadow-lg'>
        <img
          src='/assets/wood.png'
          alt='Wood Background'
          className='absolute inset-0 object-cover w-full h-full'
        />
        <div className='relative h-full'>
          <div className='flex items-center justify-between h-full px-2 xs:px-4 sm:px-6 md:px-8 lg:px-12'>
            Left Logo - Optimized for 1112x800
            <div
              className='w-10 h-10 sm:w-12 sm:h-12 md:w-16 md:h-16 lg:w-20 lg:h-20 relative flex flex-col items-center justify-center cursor-pointer hover:scale-105 transition-transform overflow-hidden'
              aria-label='Open Bet/Table Menu'
            >
              <div className='relative w-12 h-12 sm:w-10 sm:h-10 md:w-12 md:h-12 lg:w-16 lg:h-16'>
                <Image
                  src='/assets/logo.png'
                  alt='Casino Wars Logo'
                  fill
                  className='object-contain'
                  sizes='(max-width: 640px) 32px, (max-width: 768px) 40px, (max-width: 1024px) 48px, (max-width: 1280px) 64px, 64px'
                  priority
                />
              </div>
              <span className='text-yellow-300 text-xs sm:text-sm lg:text-base -mt-1'>
                Table: {gameState?.table_number}
              </span>
            </div>

            Center Hats - Optimized for 1112x800
            <div className='flex items-center justify-center gap-1 sm:gap-2 md:gap-3 lg:gap-4'>
              Generate 6 hat slots for players
              {Array.from({ length: 6 }, (_, index) => {
                const playerId = `player${index + 1}`
                const playerData = gameState?.players?.[playerId]
                const isActive = playerData?.status === 1

                return (
                  <div
                    key={playerId}
                    className='relative w-6 h-6 sm:w-8 sm:h-8 md:w-10 md:h-10 lg:w-12 lg:h-12 cursor-pointer hover:scale-110 transition-transform duration-200'
                    onClick={e => {
                      e.stopPropagation()
                      if (isActive) {
                        deactivatePlayer(playerId)
                      } else {
                        activatePlayer(playerId)
                      }
                    }}
                    aria-label={`Toggle Player ${index + 1} - ${
                      isActive ? 'Active' : 'Inactive'
                    }`}
                  >
                    <Image
                      src={
                        isActive ? '/assets/whitehat.png' : '/assets/redhat.png'
                      }
                      alt={`Player ${index + 1} Hat`}
                      fill
                      className='object-contain drop-shadow-lg'
                      sizes='(max-width: 640px) 24px, (max-width: 768px) 32px, (max-width: 1024px) 40px, (max-width: 1280px) 48px, 48px'
                      priority
                    />
                  </div>
                )
              })}
            </div>

            Right Logo - Optimized for 1112x800
            <div
              className='w-10 h-10 sm:w-12 sm:h-12 md:w-16 md:h-16 lg:w-20 lg:h-20 relative flex items-center justify-center cursor-pointer hover:scale-105 transition-transform overflow-hidden'
              aria-label='Open Game Menu'
            >
              <div className='relative w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12 lg:w-16 lg:h-16'>
                <Image
                  src='/assets/menu.png'
                  alt='Menu Icon'
                  fill
                  className='object-contain'
                  sizes='(max-width: 640px) 32px, (max-width: 768px) 40px, (max-width: 1024px) 48px, (max-width: 1280px) 64px, 64px'
                  priority
                />
              </div>
            </div>
          </div>
        </div>
      </nav> */}

      {/* Main Content Area - Full width */}
      <div className="pt-[14vh]">
        <div className="border-2 border-yellow-500 bg-[#911606] mx-auto flex flex-col gap-6 p-4 relative z-10">
          {/* Dealer Window */}
          <div className="flex justify-center">
            <div
              className={`w-full rounded-2xl ${gameState?.game_phase === "dealer"
                ? "bg-yellow-300 border-2 border-yellow-500 text-gray-900 shadow-2xl shadow-yellow-500/25 ring-2 ring-yellow-400"
                : "bg-[#911606] text-white"
                }`}
            >
              <div className="flex items-center justify-between mb-4">
                {/* <h2 className={`text-xl font-bold flex items-center ${gameState?.game_phase === "dealer" ? "text-gray-900" : "text-white"
                }`}>
                <svg className={`w-5 h-5 mr-2 ${gameState?.game_phase === "dealer" ? "text-gray-900" : "text-blue-400"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"
                  />
                </svg>
                Dealer Status
              </h2>
              <div className="flex items-center space-x-3">
                <div
                  className={`px-3 py-1 rounded-lg text-sm font-medium ${gameState?.dealer?.status === "playing"
                    ? "bg-green-500/20 text-green-400 border border-green-500/30"
                    : gameState?.dealer?.status === "bust"
                      ? "bg-red-500/20 text-red-400 border border-red-500/30"
                      : "bg-gray-500/20 text-gray-400 border border-gray-500/30"
                    }`}
                >
                  {gameState?.dealer?.status || "waiting"}
                </div>
                <div className={`text-sm ${gameState?.game_phase === "dealer" ? "text-gray-900" : "text-gray-400"}`}>
                  Cards: {gameState?.deck_count || 0}
                </div>
              </div> */}
              </div>

              <div className="bg-black/20 rounded-lg p-2 border-2 border-yellow-500 border-dashed">
                {/* Main horizontal layout */}
                <div className="flex items-start justify-between ">
                  {/* Left: Dealer's Cards text */}
                  <div className="text-base font-medium text-white flex-shrink-0">
                    Dealer's Cards
                  </div>
                  {/* Right: Total and buttons */}
                  <div className="flex flex-col items-end gap-y-2 flex-shrink-0">
                    <button
                      onClick={() =>
                        sendWebSocketMessage({ action: "reset_round" })
                      }
                      className="px-2 py-1 bg-white text-[#911606] rounded-md transition-all duration-300 transform hover:scale-105 hover:shadow-xl shadow-lg flex items-center justify-center space-x-3"
                    >
                      New Game
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Players Grid - 2 per row */}
          <div className="grid grid-cols-3 gap-2">
            {Object.entries(gameState?.players || {}).map(
              ([playerId, playerData]) => {
                const isCurrentHand =
                  gameState?.selected_hand?.player_id === playerId &&
                  gameState?.selected_hand?.hand_index === 0 &&
                  gameState?.selected_hand?.split_level === 0;

                const isCurrentSplit1Hand =
                  gameState?.selected_hand?.player_id === playerId &&
                  gameState?.selected_hand?.hand_index === 0 &&
                  gameState?.selected_hand?.split_level === 1;

                const isCurrentSplit2Hand =
                  gameState?.selected_hand?.player_id === playerId &&
                  gameState?.selected_hand?.hand_index === 0 &&
                  gameState?.selected_hand?.split_level === 2;

                const isActive = playerData.status === 1;
                return (
                  <div
                    key={playerId}
                    className={`p-3 rounded-xl transition-all duration-300 transform hover:scale-[1.02] ${"bg-[#C1351D] text-gray-200 border border-red-500/30"
                      // isCurrentHand
                      //   ? 'bg-gradient-to-br from-blue-600/80 to-blue-500/80 text-white shadow-xl border border-blue-400/30'
                      //   : isActive
                      //   ? 'bg-gradient-to-br from-blue-600/80 to-blue-500/80 text-white shadow-xl border border-blue-400/30'
                      //   : 'bg-gradient-to-br from-red-700/80 to-red-600/80 text-gray-200 border border-red-500/30'
                      }`}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (isActive) {
                        handlePlayerClick(playerId);
                      }
                    }}
                  >
                    <div className="flex flex-col space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          {/* <div
                            className={`w-4 h-4 rounded-full shadow-lg ${
                              isCurrentHand
                                ? 'bg-blue-400 animate-pulse'
                                : isActive
                                ? 'bg-green-400 animate-pulse'
                                : 'bg-gray-400'
                            }`}
                          /> */}
                          <div>
                            <div className={`text-lg font-bold text-white`}>
                              {playerId.replace("player", "Player ")}
                            </div>
                            {/* <div
                              className={`text-sm ${
                                isCurrentHand ? 'text-gray-700' : 'opacity-75'
                              }`}
                            >
                              {isCurrentHand
                                ? 'Current Hand'
                                : isActive
                                ? 'Active'
                                : 'Inactive'}
                            </div> */}
                          </div>
                          {isActive && (
                            <>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  sendWebSocketMessage({
                                    action: "handle_manual_insurance",
                                    player_id: playerId,
                                  });
                                }}
                                className={`px-1 py-0.5 rounded transition-colors text-sm ${gameState?.players?.[playerId]?.insurence ===
                                  1
                                  ? "bg-gray-500 text-white hover:bg-gray-600"
                                  : "bg-yellow-500 text-white hover:bg-yellow-600"
                                  }`}
                              >
                                {gameState?.players?.[playerId]?.insurence === 1
                                  ? "Cancel Insurance"
                                  : "Insurance"}
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (
                                    gameState?.players?.[playerId]
                                      ?.even_money === 1
                                  ) {
                                    sendWebSocketMessage({
                                      action: "no_for_player_even_money",
                                      player_id: playerId,
                                    });
                                  } else {
                                    sendWebSocketMessage({
                                      action: "yes_for_player_even_money",
                                      player_id: playerId,
                                    });
                                  }
                                }}
                                className={`px-1 py-0.5 rounded transition-colors text-sm ${gameState?.players?.[playerId]?.even_money ===
                                  1
                                  ? "bg-gray-500 text-white hover:bg-gray-600"
                                  : "bg-purple-500 text-white hover:bg-purple-600"
                                  }`}
                              >
                                {gameState?.players?.[playerId]?.even_money ===
                                  1
                                  ? "Cancel Even Money"
                                  : "Even Money"}
                              </button>
                            </>
                          )}
                        </div>
                        {/* {!isActive ? (
                          <button
                            onClick={e => {
                              e.stopPropagation()
                              activatePlayer(playerId)
                            }}
                            className='px-1 py-0.5 bg-white text-[#450A03] rounded-md flex items-center text-sm '
                          >
                            <span>Activate</span>
                          </button>
                        ) : (
                          <button
                            onClick={e => {
                              e.stopPropagation()
                              deactivatePlayer(playerId)
                            }}
                            className={`px-1 py-0.5 bg-black/20 border border-white rounded-md flex items-center text-sm `}
                          >
                            <span>Deactivate</span>
                          </button>
                        )} */}
                      </div>
                      {isActive && (
                        <div className="space-y-2">
                          {/* Main Hand */}
                          <div
                            className={`rounded-lg p-2 ${getHandBoxColor(
                              isHandSelected(gameState, playerId, 0, 0) &&
                              gameState?.current_player === playerId,
                              gameState?.players?.[playerId]?.hands?.[0]?.result
                            )}`}
                          >
                            <div className="flex items-center justify-between mb-2">
                              <div
                                className={`text-sm font-medium ${isCurrentHand ? "text-gray-900" : "text-white"
                                  }`}
                              >
                                Main Hand:
                              </div>
                            </div>

                            <div className="flex flex-wrap justify-center items-center gap-1">
                              <>
                                <button
                                  onClick={() =>
                                    sendWebSocketMessage({
                                      action: "manual_make_win",
                                      player_id: playerId,
                                      split_level: 0,
                                      hand_index: 0,
                                    })
                                  }
                                  className="px-1 bg-green-500 text-white rounded hover:bg-green-600 transition-colors border-2 border-white text-lg"
                                >
                                  MAKE WIN
                                </button>
                                <button
                                  onClick={() =>
                                    sendWebSocketMessage({
                                      action: "manual_make_lose",
                                      player_id: playerId,
                                      split_level: 0,
                                      hand_index: 0,
                                    })
                                  }
                                  className="px-1 bg-red-500 text-white rounded hover:bg-red-600 transition-colors border-2 border-white text-lg"
                                >
                                  MAKE LOSE
                                </button>
                                <button
                                  onClick={() =>
                                    sendWebSocketMessage({
                                      action: "manual_make_tie",
                                      player_id: playerId,
                                      split_level: 0,
                                      hand_index: 0,
                                    })
                                  }
                                  className="px-1 bg-purple-500 text-white rounded hover:bg-purple-600 transition-colors border-2 border-white text-lg"
                                >
                                  MAKE PUSH
                                </button>
                                <button
                                  onClick={() =>
                                    sendWebSocketMessage({
                                      action: "manual_make_default",
                                      player_id: playerId,
                                      split_level: 0,
                                      hand_index: 0,
                                    })
                                  }
                                  className="px-1 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors border-2 border-white text-lg"
                                >
                                  DEFAULT
                                </button>
                                {/* Surrender Button - Only show if hand has exactly 2 cards and dealer's upcard is not Ace */}
                                <button
                                  onClick={() => {
                                    sendWebSocketMessage({
                                      action: "manual_make_surrender",
                                      player_id: playerId,
                                      split_level: 0,
                                      hand_index: 0,
                                    });
                                  }}
                                  className="px-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors border-2 border-white text-lg"
                                >
                                  SURRENDER
                                </button>
                              </>
                            </div>
                          </div>

                          {/* Split1 Hand */}
                          {gameState?.players?.[playerId]?.split1_status ===
                            1 ? (
                            <div className="mt-4">
                              <div
                                className={`rounded-lg p-2 ${getHandBoxColor(
                                  isHandSelected(gameState, playerId, 0, 1) &&
                                  gameState?.current_player === playerId,
                                  gameState.players[playerId].split1[0].result
                                )}`}
                              >
                                <div className="flex items-center justify-between mb-2">
                                  <div
                                    className={`text-sm font-medium ${isCurrentSplit1Hand
                                      ? "text-gray-900"
                                      : "text-white"
                                      }`}
                                  >
                                    Split 1:
                                  </div>
                                  <button
                                    onClick={() =>
                                      sendWebSocketMessage({
                                        action: "deactivate_split1",
                                        player_id: playerId,
                                      })
                                    }
                                    className="px-1 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors border-2 border-white text-lg"
                                  >
                                    Deactivate Split
                                  </button>
                                </div>
                                <div className="flex flex-wrap justify-center items-center gap-1">
                                  <>
                                    <button
                                      onClick={() =>
                                        sendWebSocketMessage({
                                          action: "manual_make_win",
                                          player_id: playerId,
                                          split_level: 1,
                                          hand_index: 0,
                                        })
                                      }
                                      className="px-1 bg-green-500 text-white rounded hover:bg-green-600 transition-colors border-2 border-white text-lg"
                                    >
                                      MAKE WIN
                                    </button>
                                    <button
                                      onClick={() =>
                                        sendWebSocketMessage({
                                          action: "manual_make_lose",
                                          player_id: playerId,
                                          split_level: 1,
                                          hand_index: 0,
                                        })
                                      }
                                      className="px-1 bg-red-500 text-white rounded hover:bg-red-600 transition-colors border-2 border-white text-lg"
                                    >
                                      MAKE LOSE
                                    </button>
                                    <button
                                      onClick={() =>
                                        sendWebSocketMessage({
                                          action: "manual_make_tie",
                                          player_id: playerId,
                                          split_level: 1,
                                          hand_index: 0,
                                        })
                                      }
                                      className="px-1 bg-purple-500 text-white rounded hover:bg-purple-600 transition-colors border-2 border-white text-lg"
                                    >
                                      MAKE PUSH
                                    </button>
                                    <button
                                      onClick={() =>
                                        sendWebSocketMessage({
                                          action: "manual_make_default",
                                          player_id: playerId,
                                          split_level: 1,
                                          hand_index: 0,
                                        })
                                      }
                                      className="px-1 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors border-2 border-white text-lg"
                                    >
                                      DEFAULT
                                    </button>

                                  </>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <div className="mt-4">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  sendWebSocketMessage({
                                    action: "activate_split1",
                                    player_id: playerId,
                                  });
                                }}
                                className="px-3 py-1 bg-purple-500 text-white rounded hover:bg-purple-600 transition-colors text-lg"
                              >
                                Activate Split1
                              </button>
                            </div>
                          )}

                          {/* Split2 Hand */}
                          {gameState?.players?.[playerId]?.split2_status ===
                            1 ? (
                            <div className="mt-4">
                              <div
                                className={`rounded-lg p-2 ${getHandBoxColor(
                                  isHandSelected(gameState, playerId, 0, 2) &&
                                  gameState?.current_player === playerId,
                                  gameState.players[playerId].split2[0].result
                                )}`}
                              >
                                <div className="flex items-center justify-between mb-2">
                                  <div
                                    className={`text-sm font-medium ${isCurrentSplit2Hand
                                      ? "text-gray-900"
                                      : "text-white"
                                      }`}
                                  >
                                    Split 2:
                                  </div>
                                  <button
                                    onClick={() =>
                                      sendWebSocketMessage({
                                        action: "deactivate_split2",
                                        player_id: playerId,
                                      })
                                    }
                                    className="px-1 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors border-2 border-white text-lg"
                                  >
                                    Deactivate Split
                                  </button>
                                </div>

                                <div className="flex flex-wrap justify-center items-center gap-1">
                                  <>
                                    <button
                                      onClick={() =>
                                        sendWebSocketMessage({
                                          action: "manual_make_win",
                                          player_id: playerId,
                                          split_level: 2,
                                          hand_index: 0,
                                        })
                                      }
                                      className="px-1 bg-green-500 text-white rounded hover:bg-green-600 transition-colors border-2 border-white text-lg"
                                    >
                                      MAKE WIN
                                    </button>
                                    <button
                                      onClick={() =>
                                        sendWebSocketMessage({
                                          action: "manual_make_lose",
                                          player_id: playerId,
                                          split_level: 2,
                                          hand_index: 0,
                                        })
                                      }
                                      className="px-1 bg-red-500 text-white rounded hover:bg-red-600 transition-colors border-2 border-white text-lg"
                                    >
                                      MAKE LOSE
                                    </button>
                                    <button
                                      onClick={() =>
                                        sendWebSocketMessage({
                                          action: "manual_make_tie",
                                          player_id: playerId,
                                          split_level: 2,
                                          hand_index: 0,
                                        })
                                      }
                                      className="px-1 bg-purple-500 text-white rounded hover:bg-purple-600 transition-colors border-2 border-white text-lg"
                                    >
                                      MAKE PUSH
                                    </button>
                                    <button
                                      onClick={() =>
                                        sendWebSocketMessage({
                                          action: "manual_make_default",
                                          player_id: playerId,
                                          split_level: 2,
                                          hand_index: 0,
                                        })
                                      }
                                      className="px-1 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors border-2 border-white text-lg"
                                    >
                                      DEFAULT
                                    </button>


                                    {/* <button
                                      onClick={() =>
                                        sendWebSocketMessage({
                                          action: 'deactivate_split2',
                                          player_id: playerId
                                        })
                                      }
                                      className='px-1 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors border-2 border-white'
                                    >
                                      Deactivate Split
                                    </button> */}
                                  </>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <div className="mt-4">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  sendWebSocketMessage({
                                    action: "activate_split2",
                                    player_id: playerId,
                                  });
                                }}
                                className="px-3 py-1 bg-purple-500 text-white rounded hover:bg-purple-600 transition-colors text-lg"
                              >
                                Activate Split2
                              </button>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Next Button - Show for current player */}
                      {isActive && gameState?.current_turn === "player" && (
                        <div className="mt-4 flex justify-end">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleNextTurn();
                            }}
                            className="px-3 py-1.5 bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white rounded-lg transition-all duration-300 transform hover:scale-105 shadow-lg flex items-center space-x-2 text-lg"
                          >
                            <svg
                              className="w-4 h-4"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M13 5l7 7-7 7M5 5l7 7-7 7"
                              />
                            </svg>
                            <span>Next</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              }
            )}
          </div>
        </div>
      </div>
      {/* DebugPanel at the end */}
      <DebugPanel gameState={gameState} />

      {/* Enhanced Popup Message */}
      {showPopup && (
        <div className="fixed top-8 left-1/2 transform -translate-x-1/2 z-50 animate-bounce">
          <div className="bg-gradient-to-r from-red-800 to-red-700 border border-red-600 text-white px-8 py-4 rounded-2xl shadow-2xl flex items-center space-x-3 backdrop-blur-xl">
            <div className="w-3 h-3 bg-gradient-to-r from-green-400 to-green-500 rounded-full animate-pulse"></div>
            <span className="font-medium text-lg">{popupMessage}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default GameMenu;
