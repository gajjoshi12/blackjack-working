"use client";
import { useState, useEffect, useRef } from "react";
// import PlayerBoard from '@/components/PlayerBoard'
import Image from "next/image";
import { getWebSocketUrl } from "@/lib/ip-config";

interface Hand {
  cards: string[];
  total: number;
  status: string;
  result?: string;
  bet?: number;
  insurence?: number;
  live_function_hand?: string;
}

interface PlayerData {
  status: number;
  hands: Hand[];
  split1: Hand[];
  split1_status: number;
  split2: Hand[];
  split2_status: number;
  insurence?: number;
  surrender?: number;
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
  evaluate_game: boolean;
  mode: string;
  round_number?: number;
  all_done?: number;
}

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
  return cards[0][0] === cards[1][0];
};

const DebugPanel = ({ gameState }: { gameState: GameState | null }) => {
  if (!gameState) return null;
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
  const [showResultPopup, setShowResultPopup] = useState(false);
  const [playerResult, setPlayerResult] = useState<string>("");
  const [resultPopupDismissed, setResultPopupDismissed] = useState(false);
  const [pairType, setPairType] = useState<string>("");
  const [showPairPopup, setShowPairPopup] = useState(false);
  const [shownPairCards, setShownPairCards] = useState<string>("");

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
      };

      ws.onclose = () => {
        console.log("Disconnected from server");
        setIsConnected(false);

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

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        setPopupMessage("⚠️ Connection error occurred");
        setShowPopup(true);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("Received:", data);

        if (data.game_state) {
          setGameState(data.game_state);
        }

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
            setShowResultPopup(false);
            setPlayerResult("");
            setResultPopupDismissed(false);
            break;
          case "round_reset":
            setIsPlaying(false);
            setIsGameStarted(false);
            setIsDealerSelected(false);
            setShowNextButton(false);
            setIsRoundFinished(true);
            setShowResultPopup(false);
            setPlayerResult("");
            setResultPopupDismissed(false);
            break;
          case "game_reset":
            setIsPlaying(false);
            setIsGameStarted(false);
            setIsRoundFinished(false);
            setShowNextButton(false);
            setIsDealerSelected(false);
            setSelectedCard(null);
            setSelectedSuit(null);
            setShowResultPopup(false);
            setPlayerResult("");
            setResultPopupDismissed(false);
            setPopupMessage(data.message);
            setShowPopup(true);
            setTimeout(() => setShowPopup(false), 3000);
            break;
          case "game_evaluated":
            setShowResultPopup(true);
            setResultPopupDismissed(false);
            // Get player6's result
            const player6Data = data.game_state?.players?.player6;
            if (player6Data) {
              const mainHandResult = player6Data.hands?.[0]?.result;
              const split1Result = player6Data.split1?.[0]?.result;
              const split2Result = player6Data.split2?.[0]?.result;

              // Determine overall result (prioritize wins, then ties, then losses)
              let overallResult = "lose";
              if (
                mainHandResult === "win" ||
                split1Result === "win" ||
                split2Result === "win"
              ) {
                overallResult = "win";
              } else if (
                mainHandResult === "tie" ||
                split1Result === "tie" ||
                split2Result === "tie"
              ) {
                overallResult = "tie";
              }

              setPlayerResult(overallResult);
            }
            break;
          // Handle manual mode result actions for player6
          case "manual_make_win":
          case "manual_make_lose":
          case "manual_make_tie":
          case "manual_make_default":
            // Check if this action affects player6
            if (data.player_id === "player6") {
              setShowResultPopup(true);
              setResultPopupDismissed(false); // Reset dismissed flag for new manual results

              // Determine result based on action
              let manualResult = "lose";
              if (data.action === "manual_make_win") {
                manualResult = "win";
              } else if (data.action === "manual_make_tie") {
                manualResult = "tie";
              } else if (data.action === "manual_make_lose") {
                manualResult = "lose";
              } else if (data.action === "manual_make_default") {
                // For default, check the actual result from game state
                const player6Data = data.game_state?.players?.player6;
                if (player6Data) {
                  const mainHandResult = player6Data.hands?.[0]?.result;
                  const split1Result = player6Data.split1?.[0]?.result;
                  const split2Result = player6Data.split2?.[0]?.result;

                  if (
                    mainHandResult === "win" ||
                    split1Result === "win" ||
                    split2Result === "win"
                  ) {
                    manualResult = "win";
                  } else if (
                    mainHandResult === "tie" ||
                    split1Result === "tie" ||
                    split2Result === "tie"
                  ) {
                    manualResult = "tie";
                  }
                }
              }

              setPlayerResult(manualResult);
            }
            break;
          case "error":
            setPopupMessage(data.message);
            setShowPopup(true);
            setTimeout(() => setShowPopup(false), 1000);
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

  // Add this useEffect after your existing useEffects
  useEffect(() => {
    // Watch for manual mode result changes in game state for player6
    if (
      gameState?.players?.player6 &&
      gameState?.mode === "manual" &&
      !showResultPopup &&
      !resultPopupDismissed // Add this condition
    ) {
      const player6Data = gameState.players.player6;
      const mainHandResult = player6Data.hands?.[0]?.result;
      const split1Result = player6Data.split1?.[0]?.result;
      const split2Result = player6Data.split2?.[0]?.result;

      // Check if any hand has a definitive result
      const hasResults = mainHandResult || split1Result || split2Result;
      const hasDefinitiveResults =
        (mainHandResult &&
          ["win", "lose", "tie", "fail"].includes(mainHandResult)) ||
        (split1Result &&
          ["win", "lose", "tie", "fail"].includes(split1Result)) ||
        (split2Result && ["win", "lose", "tie", "fail"].includes(split2Result));

      if (hasResults && hasDefinitiveResults) {
        setShowResultPopup(true);

        // Determine overall result
        let overallResult = "lose";
        if (
          mainHandResult === "win" ||
          split1Result === "win" ||
          split2Result === "win"
        ) {
          overallResult = "win";
        } else if (
          mainHandResult === "tie" ||
          split1Result === "tie" ||
          split2Result === "tie"
        ) {
          overallResult = "tie";
        }

        setPlayerResult(overallResult);
      }
    }
  }, [
    gameState?.players?.player6?.hands?.[0]?.result,
    gameState?.players?.player6?.split1?.[0]?.result,
    gameState?.players?.player6?.split2?.[0]?.result,
    gameState?.mode,
    showResultPopup,
    resultPopupDismissed, // Add this dependency
  ]);

  useEffect(() => {
    // Reset the dismissed flag when game starts or resets
    if (
      gameState?.game_phase === "playing" ||
      gameState?.game_phase === "dealing"
    ) {
      setResultPopupDismissed(false);
      setShownPairCards(""); // Reset shown pair cards for new rounds
    }
  }, [gameState?.game_phase]);

  // Pair checking functions
  const getCardSuit = (card: string): string => {
    return card.slice(-1); // Last character is the suit
  };

  const getCardRank = (card: string): string => {
    return card.slice(0, -1); // Everything except last character is the rank
  };

  const isRedSuit = (suit: string): boolean => {
    return suit === "H" || suit === "D"; // Hearts and Diamonds are red
  };

  const isBlackSuit = (suit: string): boolean => {
    return suit === "S" || suit === "C"; // Spades and Clubs are black
  };

  const checkPairType = (cards: string[]): string => {
    if (cards.length !== 2) return "";

    const card1 = cards[0];
    const card2 = cards[1];

    const rank1 = getCardRank(card1);
    const rank2 = getCardRank(card2);

    // Check if ranks are the same
    if (rank1 !== rank2) return "";

    const suit1 = getCardSuit(card1);
    const suit2 = getCardSuit(card2);

    // Royale Pair - Same rank, same suit (Perfect Pair)
    if (suit1 === suit2) {
      return "Royale Pair";
    }

    const isRed1 = isRedSuit(suit1);
    const isRed2 = isRedSuit(suit2);
    const isBlack1 = isBlackSuit(suit1);
    const isBlack2 = isBlackSuit(suit2);

    // Coloured Pair - Same rank, same color (diff. suit)
    if ((isRed1 && isRed2) || (isBlack1 && isBlack2)) {
      return "Coloured Pair";
    }

    // Mixed Pair - Same rank, red + black
    if ((isRed1 && isBlack2) || (isBlack1 && isRed2)) {
      return "Mixed Pair";
    }

    return "";
  };

  // useEffect to check for pairs
  useEffect(() => {
    if (!gameState?.players?.player6?.hands?.[0]?.cards) return;

    const mainHandCards = gameState.players.player6.hands[0].cards;

    // Only check main hand when round_number is 0 and exactly 2 cards
    if (gameState?.round_number === 0 && mainHandCards.length === 2) {
      const pairType = checkPairType(mainHandCards);
      const cardsString = mainHandCards.sort().join(",");

      if (pairType && !showPairPopup && cardsString !== shownPairCards) {
        setPairType(pairType);
        setShownPairCards(cardsString);
        sendWebSocketMessage({
          action: "set_live_function_hand",
          player_id: "player6",
          split_level: 0,
          hand_index: 0,
          value: `${pairType}`,
        });
        setShowPairPopup(true);
      }
    }
  }, [
    gameState?.players?.player6?.hands?.[0]?.cards,
    gameState?.round_number,
    showPairPopup,
    shownPairCards,
  ]);

  const handleMainContainerClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
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

    sendWebSocketMessage({
      action: "select_player",
      player_id: playerId,
    });

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

    const activePlayers = getActivePlayers();
    if (activePlayers.length === 0) {
      setPopupMessage("⚠️ No active players");
      setShowPopup(true);
      setTimeout(() => setShowPopup(false), 3000);
      return;
    }

    sendWebSocketMessage({
      action: "start_game",
    });

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

    setIsPlaying(false);
    setIsGameStarted(false);
    setIsRoundFinished(false);
    setShowNextButton(false);
    setIsDealerSelected(false);
    setSelectedCard(null);
    setSelectedSuit(null);

    sendWebSocketMessage({
      action: "reset_game",
    });

    setPopupMessage("🔄 Game has been reset");
    setShowPopup(true);
    setTimeout(() => setShowPopup(false), 3000);
  };

  const assignCard = () => {
    if (gameState?.game_phase === "dealer" && selectedCard && selectedSuit) {
      const cardCode = selectedCard + selectedSuit;
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
    if (!gameState?.players[gameState.selected_hand.player_id]?.status) {
      setPopupMessage("⚠️ Player must be active to add cards");
      setShowPopup(true);
      setTimeout(() => setShowPopup(false), 3000);
      return;
    }
    const cardCode = selectedCard + selectedSuit;
    sendWebSocketMessage({
      action: "hit_player",
      player_id: gameState.selected_hand.player_id,
      hand_index: gameState.selected_hand.hand_index,
      card: cardCode,
    });
    setSelectedCard(null);
    setSelectedSuit(null);
  };

  const handleInsurance = (playerId: string) => {
    sendWebSocketMessage({
      action: "handle_insurence",
      player_id: playerId,
    });
    setInsuranceState((prev) => ({ ...prev, [playerId]: true }));
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

  const player6Active = gameState?.players?.player6?.status === 1;

  // Helper to get hand color class (match dealer/auto/page.tsx)
  const getHandBoxColor = (
    selected: boolean,
    isActive: boolean,
    result?: string
  ) => {
    if (selected && gameState?.all_done === 1)
      return "bg-yellow-300 border-2 border-yellow-500";
    if (result === "surrender")
      return "bg-blue-500 border-2 border-blue-700 text-white";
    if (result === "fail")
      return "bg-red-500 border-2 border-red-700 text-white";
    if (result === "win")
      return "bg-green-500 border-2 border-green-700 text-white";
    if (result === "tie")
      return "bg-purple-500 border-2 border-purple-700 text-white";
    if (isActive) return " text-white border-2 border-yellow-500";
    // return 'bg-gradient-to-br from-red-700/80 to-red-600/80 text-gray-200 border border-red-500/30'
  };

  return (
    <div className="min-h-screen w-screen bg-[#450A03]">
      {player6Active ? (
        <div className="min-h-screen bg-[#450A03] text-white p-8">
          <nav className="fixed top-0 left-0 right-0 h-[12vh] w-full overflow-hidden z-50 shadow-lg">
            <img
              src="/assets/wood.png"
              alt="Wood Background"
              className="absolute inset-0 object-cover w-full h-full"
            />
            <div className="relative h-full">
              <div className="flex items-center justify-between h-full px-2 xs:px-4 sm:px-6 md:px-8 lg:px-12">
                {/* Left Logo */}
                <div
                  className="w-10 h-10 sm:w-12 sm:h-12 md:w-16 md:h-16 lg:w-20 lg:h-20 relative flex flex-col items-center justify-center cursor-pointer hover:scale-105 transition-transform overflow-hidden"
                  aria-label="Open Bet/Table Menu"
                >
                  <div className="relative w-12 h-12 sm:w-10 sm:h-10 md:w-12 md:h-12 lg:w-16 lg:h-16">
                    <Image
                      src="/assets/logo.png"
                      alt="Casino Wars Logo"
                      fill
                      className="object-contain"
                      sizes="(max-width: 640px) 32px, (max-width: 768px) 40px, (max-width: 1024px) 48px, (max-width: 1280px) 64px, 64px"
                      priority
                    />
                  </div>
                  <span className="text-yellow-300 text-xs sm:text-sm lg:text-base -mt-1">
                    Table: {gameState?.table_number}
                  </span>
                </div>

                <div className="flex items-center justify-center gap-1 sm:gap-2 md:gap-3 lg:gap-4">
                  <div className="relative w-20 h-20 cursor-pointer hover:scale-110 transition-transform duration-200">
                    <Image
                      src="/assets/ocean7.png"
                      alt={`Logo`}
                      fill
                      className="object-contain drop-shadow-lg"
                      sizes="(max-width: 640px) 24px, (max-width: 768px) 32px, (max-width: 1024px) 40px, (max-width: 1280px) 48px, 48px"
                      priority
                    />
                  </div>
                </div>

                {/* Right Logo */}
                <div
                  className="w-10 h-10 sm:w-12 sm:h-12 md:w-16 md:h-16 lg:w-20 lg:h-20 relative flex items-center justify-center cursor-pointer hover:scale-105 transition-transform overflow-hidden mr-4"
                  aria-label="Open Game Menu"
                >
                  <div className="flex flex-col items-end justify-center w-full h-full">
                    <h1 className="text-yellow-500">Bets: </h1>
                    <span className="text-yellow-500">min: 0</span>
                    <span className="text-yellow-500">max: 0</span>
                  </div>
                </div>
              </div>
            </div>
          </nav>

          {/* Main Content Area */}
          <div className="pt-[8vh]">
            <div className="mx-auto max-w-7xl px-4">
              <div className="bg-[#911606] border-4 border-[#d4af37] p-6 w-full grow flex flex-col rounded-lg">
                {/* Player Number and Status */}
                <div className="text-center mb-4">
                  <h2 className="text-3xl sm:text-4xl font-semibold text-[#d4af37] font-[questrial] tracking-widest mb-2">
                    PLAYER 6
                  </h2>

                  {/* Status Display */}
                  {/* <div className='flex justify-center'>
                    <div className='inline-block px-4 sm:px-6 py-1.5 sm:py-2 bg-[#7a1105] text-white font-semibold rounded shadow-md'>
                      <span className='font-semibold'>Status: </span>
                      <span className='text-yellow-300'>
                        {gameState?.players?.player6?.status === 1
                          ? 'Active'
                          : 'Inactive'}
                      </span>
                      {gameState?.game_phase && (
                        <>
                          <span className='mx-2'>|</span>
                          <span className='font-semibold'>Phase: </span>
                          <span className='text-green-300'>
                            {gameState.game_phase}
                          </span>
                        </>
                      )}
                    </div>
                  </div> */}
                </div>

                {/* Dealer Section */}
                <div className="relative bg-[#a42210] border-2 border-[#d4af37] p-4 sm:p-6 rounded-xl mb-6 sm:mb-8 shadow-md">
                  <h3 className="text-xl font-medium font-[questrial] tracking-widest text-white mb-4">
                    Dealer's Hand
                  </h3>

                  <div className="flex justify-center items-center gap-4 min-h-[120px] mb-4">
                    {gameState.mode !== "manual" &&
                      gameState?.dealer?.cards?.map(
                        (card: string, index: number) => (
                          <div
                            key={index}
                            className="w-36 h-52 transform hover:scale-110 transition-transform duration-200"
                          >
                            <img
                              src={`/cards/${card}.png`}
                              alt={card}
                              className="w-full h-full object-contain drop-shadow-xl"
                            />
                          </div>
                        )
                      )}
                    {gameState.mode !== "manual" &&
                      [
                        ...Array(
                          Math.max(
                            0,
                            2 - (gameState?.dealer?.cards?.length || 0)
                          )
                        ),
                      ].map((_, index) => (
                        <div
                          key={`empty-${index}`}
                          className="w-36 h-52 border-2 border-dashed border-gray-400 rounded-lg flex items-center justify-center bg-gray-800/50 transform hover:scale-110 transition-transform duration-200"
                        >
                          <span className="text-gray-400 text-xs">Empty</span>
                        </div>
                      ))}
                  </div>
                  <div className="absolute top-[93%] left-[43%] text-center">
                    <div className="inline-block bg-[#911606] px-3 py-1 rounded-full text-sm font-bold text-[#d4af37] border-2 border-[#d4af37]">
                      Total: {dealerTotal}
                    </div>
                  </div>

                  {gameState?.game_phase === "dealer" && (
                    <div className="flex items-center justify-center space-x-3 mt-4"></div>
                  )}
                </div>

                {/* Player 6 - Large Panel */}
                {gameState?.players?.player6 && (
                  <div className="text-center">
                    <div
                      className="bg-[#a42210] border-2 border-[#d4af37] p-10  rounded-xl shadow-md transition-all duration-300 relative"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (gameState.players.player6.status === 1) {
                          handlePlayerClick("player6");
                        }
                      }}
                    >
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-4">
                          <div>
                            <div
                              className={`text-xl font-medium font-[questrial] tracking-widest text-white}`}
                            >
                              Your Hand
                              {gameState.players.player6.insurence === 1 && (
                                <span className="ml-3 text-yellow-400 text-base font-semibold">
                                  Insured
                                </span>
                              )}
                              {gameState.players.player6.even_money === 1 && (
                                <span className="ml-3 text-purple-400 text-base font-semibold">
                                  Even Money
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>

                      {gameState.players.player6.status === 1 && (
                        <div className="space-y-6">
                          {/* Main Hand */}
                          <div
                            className={`rounded-xl p-4 relative ${getHandBoxColor(
                              isHandSelected(gameState, "player6", 0, 0) &&
                              gameState?.current_player === "player6",
                              gameState.players.player6.status === 1,
                              gameState.players.player6.hands[0]?.result
                            )}`}
                          >
                            <div className="text-left mb-1">
                              <div
                                className={`text-lg font-medium ${isHandSelected(gameState, "player6", 0, 0)
                                  ? "text-gray-950"
                                  : "text-white"
                                  }`}
                              >
                                Main Hand
                              </div>
                            </div>
                            <div className="flex justify-center items-center gap-4 mb-4">
                              {gameState.players.player6.hands[0]?.cards?.map(
                                (card: string, index: number) => (
                                  <div
                                    key={index}
                                    className="relative w-36 h-52 transform hover:scale-110 transition-transform duration-200 group"
                                  >
                                    <img
                                      src={`/cards/${card}.png`}
                                      alt={card}
                                      className="w-full h-full object-contain"
                                      onError={(e) => {
                                        const target =
                                          e.target as HTMLImageElement;
                                        target.src = "/cards/back.png";
                                      }}
                                    />
                                  </div>
                                )
                              )}
                              {/* Only show empty slots if not manual mode */}
                              {gameState.mode !== "manual" &&
                                [
                                  ...Array(
                                    Math.max(
                                      0,
                                      2 -
                                      (gameState.players.player6.hands[0]
                                        ?.cards?.length ?? 0)
                                    )
                                  ),
                                ].map((_, index) => (
                                  <div
                                    key={`empty-${index}`}
                                    className="w-36 h-52 border-2 border-dashed border-gray-400 rounded-lg flex items-center justify-center bg-gray-800/50"
                                  />
                                ))}
                            </div>
                            {gameState.mode !== "manual" && (
                              <div className="absolute top-[90%] left-[43%] text-center">
                                <div className="inline-block bg-[#911606] px-3 py-1 rounded-full text-sm font-bold text-[#d4af37] border-2 border-[#d4af37]">
                                  Total:{" "}
                                  {gameState.players.player6.hands[0]?.total ??
                                    0}
                                </div>
                              </div>
                            )}

                            {/* Action Buttons */}
                            {/* Action Buttons */}
                            <div className="flex justify-center gap-4 flex-wrap mt-2 mb-4">
                              {gameState?.round_number !== 0 &&
                                isHandSelected(gameState, "player6", 0, 0) &&
                                gameState?.current_player === "player6" &&
                                gameState.players.player6.hands[0]?.cards
                                  ?.length === 2 &&
                                canSplit(
                                  gameState.players.player6.hands[0].cards
                                ) &&
                                gameState.players.player6.hands[0].status ===
                                "playing" &&
                                !gameState.players.player6.hands[0]?.live_function_hand &&
                                (gameState.players.player6.split1_status ===
                                  0 ||
                                  gameState.players.player6.split2_status ===
                                  0) && (
                                  <button
                                    onClick={() => {
                                      if (gameState?.mode === "live") {
                                        sendWebSocketMessage({
                                          action: "set_live_function_hand",
                                          player_id: "player6",
                                          split_level: 0,
                                          hand_index: 0,
                                          value: "Split",
                                        });
                                      }
                                      if (
                                        gameState?.mode === "auto" ||
                                        gameState?.mode === "manual"
                                      ) {
                                        sendWebSocketMessage({
                                          action: "split_player_auto",
                                          player_id: "player6",
                                        });
                                      }
                                    }}
                                    className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 transition-colors"
                                  >
                                    Split
                                  </button>
                                )}

                              {/* Main Hand Action Buttons for Player 6 */}
                              {gameState?.round_number !== 0 &&
                                !gameState.players.player6.hands[0]?.live_function_hand && (
                                  <>
                                    {gameState?.dealer?.cards?.[0]?.[0] === "A" &&
                                      !insuranceState[`player6_0_0`] &&
                                      !gameState.players.player6.hands[0]
                                        .insurence &&
                                      gameState.players.player6.split1_status ===
                                      0 &&
                                      gameState.players.player6.split2_status ===
                                      0 &&
                                      gameState.players.player6.hands[0]
                                        ?.total !== 21 &&
                                      gameState.players.player6.hands[0]?.cards
                                        ?.length === 2 &&
                                      gameState.players.player6.insurence ===
                                      0 && (
                                        <>
                                          <button
                                            onClick={() => {
                                              if (gameState?.mode === "live") {
                                                handleInsurance("player6");
                                              }
                                              if (
                                                gameState?.mode === "auto" ||
                                                gameState?.mode === "manual"
                                              ) {
                                                handleInsurance("player6");
                                              }
                                            }}
                                            className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors"
                                          >
                                            Insurance
                                          </button>
                                          <button
                                            onClick={() => {
                                              sendWebSocketMessage({
                                                action: "no_for_player_insurence",
                                                player_id: "player6",
                                              });
                                            }}
                                            className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
                                          >
                                            No Insurance
                                          </button>
                                        </>
                                      )}
                                    {/* Even Money Button: Only show if dealer's first card is Ace, hand has 2 cards, total is 21, and even money not taken */}
                                    {gameState?.round_number !== 0 &&
                                      gameState?.dealer?.cards?.[0]?.[0] ===
                                      "A" &&
                                      gameState.players.player6.split1_status ===
                                      0 &&
                                      gameState.players.player6.split2_status ===
                                      0 &&
                                      gameState.players.player6.hands[0]?.cards
                                        ?.length === 2 &&
                                      gameState.players.player6.hands[0]
                                        ?.total === 21 &&
                                      gameState.players.player6.even_money ===
                                      0 && (
                                        <>
                                          <button
                                            onClick={() => {
                                              sendWebSocketMessage({
                                                action:
                                                  "yes_for_player_even_money",
                                                player_id: "player6",
                                              });
                                            }}
                                            className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors"
                                          >
                                            Even Money
                                          </button>
                                          <button
                                            onClick={() => {
                                              sendWebSocketMessage({
                                                action:
                                                  "no_for_player_even_money",
                                                player_id: "player6",
                                              });
                                            }}
                                            className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
                                          >
                                            No Even Money
                                          </button>
                                        </>
                                      )}
                                    {/* Surrender Button - Only show if hand has exactly 2 cards and dealer's upcard is not Ace */}
                                    {gameState?.round_number !== 0 &&
                                      gameState?.players?.player6?.hands[0]?.cards
                                        ?.length === 2 &&
                                      gameState?.dealer?.cards?.[0]?.[0] !==
                                      "A" &&
                                      gameState.players.player6.surrender ===
                                      0 && (
                                        <>
                                          <button
                                            onClick={() => {
                                              sendWebSocketMessage({
                                                action: "surrender_player",
                                                player_id: "player6",
                                                hand_index: 0,
                                              });
                                              clearInsuranceForHand(
                                                "player6",
                                                0,
                                                0
                                              );
                                            }}
                                            className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                                          >
                                            Surrender
                                          </button>
                                          <button
                                            onClick={() => {
                                              sendWebSocketMessage({
                                                action: "no_for_player_surrender",
                                                player_id: "player6",
                                              });
                                            }}
                                            className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
                                          >
                                            No Surrender
                                          </button>
                                        </>
                                      )}
                                    {gameState.all_done === 1 &&
                                      isHandSelected(
                                        gameState,
                                        "player6",
                                        0,
                                        0
                                      ) &&
                                      !gameState.players.player6.hands[0]?.live_function_hand &&
                                      gameState?.current_player === "player6" && (
                                        <>
                                          <button
                                            onClick={() => {
                                              if (gameState?.mode === "live") {
                                                sendWebSocketMessage({
                                                  action:
                                                    "set_live_function_hand",
                                                  player_id: "player6",
                                                  split_level: 0,
                                                  hand_index: 0,
                                                  value: "Hit",
                                                });
                                              }
                                              sendWebSocketMessage({
                                                action: "hit_player",
                                                player_id: "player6",
                                                hand_index: 0,
                                              });
                                              clearInsuranceForHand(
                                                "player6",
                                                0,
                                                0
                                              );
                                            }}
                                            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
                                          >
                                            Hit
                                          </button>
                                          {gameState.players.player6.hands[0]
                                            ?.cards?.length === 2 && (
                                              <button
                                                onClick={() => {
                                                  if (gameState?.mode === "live") {
                                                    sendWebSocketMessage({
                                                      action:
                                                        "set_live_function_hand",
                                                      player_id: "player6",
                                                      split_level: 0,
                                                      hand_index: 0,
                                                      value: "Double",
                                                    });
                                                  }
                                                  sendWebSocketMessage({
                                                    action: "double_player",
                                                    player_id: "player6",
                                                    hand_index: 0,
                                                  });
                                                  clearInsuranceForHand(
                                                    "player6",
                                                    0,
                                                    0
                                                  );
                                                }}
                                                className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 transition-colors"
                                              >
                                                Double
                                              </button>
                                            )}
                                          <button
                                            onClick={() => {
                                              if (gameState?.mode === "live") {
                                                sendWebSocketMessage({
                                                  action:
                                                    "set_live_function_hand",
                                                  player_id: "player6",
                                                  split_level: 0,
                                                  hand_index: 0,
                                                  value: "Stand",
                                                });
                                              }
                                              sendWebSocketMessage({
                                                action: "next_turn",
                                                player_id: "player6",
                                                hand_index: 0,
                                              });
                                              clearInsuranceForHand(
                                                "player6",
                                                0,
                                                0
                                              );
                                            }}
                                            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
                                          >
                                            Stand
                                          </button>
                                        </>
                                      )}
                                  </>
                                )}
                            </div>
                            {/* STATUS TEXT MAIN HAND */}
                            {gameState.players.player6.hands[0]?.live_function_hand &&
                              !["insurence", "surrender"].includes(
                                gameState.players.player6.hands[0].live_function_hand
                              ) && (
                                <div className="absolute top-[50%] left-[50%] transform -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none">
                                  <span className="text-5xl font-extrabold text-white drop-shadow-[0_4px_4px_rgba(0,0,0,0.8)] animate-pulse tracking-widest bg-black/60 px-6 py-3 rounded-xl border-4 border-yellow-500 backdrop-blur-sm">
                                    {gameState.players.player6.hands[0].live_function_hand.toUpperCase()}
                                  </span>
                                </div>
                              )}
                          </div>

                          {/* Split1 Hand (manual mode: show if split1_status is 1) */}
                          {gameState.mode === "manual" &&
                            gameState.players.player6.split1_status === 1 && (
                              <div className="mt-4">
                                <div
                                  className={`rounded-xl p-4 relative ${getHandBoxColor(
                                    isHandSelected(
                                      gameState,
                                      "player6",
                                      0,
                                      1
                                    ) &&
                                    gameState?.current_player === "player6",
                                    gameState.players.player6.status === 1,
                                    gameState.players.player6.split1[0]?.result
                                  )}`}
                                >
                                  <div className="text-left mb-1">
                                    <div
                                      className={`text-lg font-medium text-black`}
                                    >
                                      Split Hand 1
                                    </div>
                                  </div>
                                </div>
                              </div>
                            )}

                          {/* Split2 Hand (manual mode: show if split2_status is 1) */}
                          {gameState.mode === "manual" &&
                            gameState.players.player6.split2_status === 1 && (
                              <div className="mt-4">
                                <div
                                  className={`rounded-xl p-4 relative ${getHandBoxColor(
                                    isHandSelected(
                                      gameState,
                                      "player6",
                                      0,
                                      2
                                    ) &&
                                    gameState?.current_player === "player6",
                                    gameState.players.player6.status === 1,
                                    gameState.players.player6.split2[0]?.result
                                  )}`}
                                >
                                  <div className="text-left mb-1">
                                    <div
                                      className={`text-lg font-medium text-black`}
                                    >
                                      Split Hand 2
                                    </div>
                                  </div>
                                </div>
                              </div>
                            )}

                          {/* Split1 Hand (auto mode: show if cards exist) */}
                          {gameState.mode !== "manual" &&
                            gameState.players.player6.split1[0]?.cards?.length >
                            0 && (
                              <div className="mt-4">
                                <div
                                  className={`rounded-xl p-4 relative ${getHandBoxColor(
                                    isHandSelected(
                                      gameState,
                                      "player6",
                                      0,
                                      1
                                    ) &&
                                    gameState?.current_player === "player6",
                                    gameState.players.player6.status === 1,
                                    gameState.players.player6.split1[0]?.result
                                  )}`}
                                >
                                  <div className="text-left mb-1">
                                    <div
                                      className={`text-lg font-medium text-black`}
                                    >
                                      Split Hand 1
                                    </div>
                                  </div>

                                  <div className="flex justify-center items-center gap-4 mb-4">
                                    {gameState.players.player6.split1[0].cards.map(
                                      (card, index) => (
                                        <div
                                          key={index}
                                          className="relative w-36 h-52 transform hover:scale-110 transition-transform duration-200 group"
                                        >
                                          <img
                                            src={`/cards/${card}.png`}
                                            alt={card}
                                            className="w-full h-full object-contain"
                                            onError={(e) => {
                                              const target =
                                                e.target as HTMLImageElement;
                                              target.src = "/cards/back.png";
                                            }}
                                          />
                                        </div>
                                      )
                                    )}
                                    {[
                                      ...Array(
                                        Math.max(
                                          0,
                                          2 -
                                          (gameState.players.player6.split1[0]
                                            .cards.length ?? 0)
                                        )
                                      ),
                                    ].map((_, index) => (
                                      <div
                                        key={`empty-${index}`}
                                        className="w-36 h-52 border-2 border-dashed border-gray-400 rounded-lg flex items-center justify-center bg-gray-800/50"
                                      />
                                    ))}
                                  </div>

                                  <div className="absolute top-[91%] left-[43%] text-center">
                                    <div className="inline-block bg-[#911606] px-3 py-1 rounded-full text-sm font-bold text-[#d4af37] border-2 border-[#d4af37]">
                                      Total:{" "}
                                      {gameState.players.player6.split1[0]
                                        .total ?? 0}
                                    </div>
                                  </div>

                                  {/* Split1 Hand Action Buttons for Player 6 */}
                                  <div className="flex justify-center gap-2 flex-wrap mt-2 mb-4">
                                    {gameState?.round_number !== 0 &&
                                      isHandSelected(
                                        gameState,
                                        "player6",
                                        0,
                                        1
                                      ) &&
                                      gameState?.current_player === "player6" &&
                                      gameState.players.player6.split1[0]?.cards
                                        ?.length === 2 &&
                                      canSplit(
                                        gameState.players.player6.split1[0]
                                          .cards
                                      ) &&
                                      gameState.players.player6.split1[0]
                                        .status === "playing" &&
                                      !gameState.players.player6.split1[0]?.live_function_hand &&
                                      (gameState.players.player6
                                        .split1_status === 0 ||
                                        gameState.players.player6
                                          .split2_status === 0) && (
                                        <button
                                          onClick={() => {
                                            if (gameState?.mode === "live") {
                                              sendWebSocketMessage({
                                                action:
                                                  "set_live_function_hand",
                                                player_id: "player6",
                                                split_level: 1,
                                                hand_index: 0,
                                                value: "Split",
                                              });
                                            }
                                            if (
                                              gameState?.mode === "auto" ||
                                              gameState?.mode === "manual"
                                            ) {
                                              sendWebSocketMessage({
                                                action: "split_player_auto",
                                                player_id: "player6",
                                              });
                                            }
                                          }}
                                          className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 transition-colors"
                                        >
                                          Split
                                        </button>
                                      )}

                                    {gameState?.round_number !== 0 &&
                                      isHandSelected(
                                        gameState,
                                        "player6",
                                        0,
                                        1
                                      ) &&
                                      !gameState.players.player6.split1[0]?.live_function_hand &&
                                      gameState?.current_player ===
                                      "player6" && (
                                        <>
                                          {gameState?.dealer
                                            ?.cards?.[0]?.[0] === "A" &&
                                            !insuranceState[`player6_0_1`] &&
                                            !gameState.players.player6.split1[0]
                                              .insurence &&
                                            gameState.players.player6
                                              .split1_status === 0 &&
                                            gameState.players.player6
                                              .split2_status === 0 &&
                                            gameState.players.player6.split1[0]
                                              ?.cards?.length === 2 &&
                                            gameState.players.player6
                                              .insurence !== 1 && (
                                              <button
                                                onClick={() => {
                                                  if (
                                                    gameState?.mode ===
                                                    "auto" ||
                                                    gameState?.mode === "manual"
                                                  ) {
                                                    handleInsurance("player6");
                                                  }
                                                }}
                                                className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors"
                                              >
                                                Insurance
                                              </button>
                                            )}
                                          <button
                                            onClick={() => {
                                              if (gameState?.mode === "live") {
                                                sendWebSocketMessage({
                                                  action:
                                                    "set_live_function_hand",
                                                  player_id: "player6",
                                                  split_level: 1,
                                                  hand_index: 0,
                                                  value: "Hit",
                                                });
                                              }
                                              if (
                                                gameState?.mode === "auto" ||
                                                gameState?.mode === "manual"
                                              ) {
                                                sendWebSocketMessage({
                                                  action: "hit_player",
                                                  player_id: "player6",
                                                  hand_index: 0,
                                                });
                                                clearInsuranceForHand(
                                                  "player6",
                                                  0,
                                                  1
                                                );
                                              }
                                            }}
                                            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
                                          >
                                            Hit
                                          </button>
                                          {gameState?.players?.player6
                                            ?.split1?.[0]?.cards?.length ===
                                            2 && (
                                              <button
                                                onClick={() => {
                                                  if (
                                                    gameState?.mode === "live"
                                                  ) {
                                                    sendWebSocketMessage({
                                                      action:
                                                        "set_live_function_hand",
                                                      player_id: "player6",
                                                      split_level: 1,
                                                      hand_index: 0,
                                                      value: "Double",
                                                    });
                                                  }
                                                  if (
                                                    gameState?.mode === "auto" ||
                                                    gameState?.mode === "manual"
                                                  ) {
                                                    sendWebSocketMessage({
                                                      action: "double_player",
                                                      player_id: "player6",
                                                      hand_index: 0,
                                                    });
                                                    clearInsuranceForHand(
                                                      "player6",
                                                      0,
                                                      1
                                                    );
                                                  }
                                                }}
                                                className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 transition-colors"
                                              >
                                                Double
                                              </button>
                                            )}
                                          <button
                                            onClick={() => {
                                              if (gameState?.mode === "live") {
                                                sendWebSocketMessage({
                                                  action:
                                                    "set_live_function_hand",
                                                  player_id: "player6",
                                                  split_level: 1,
                                                  hand_index: 0,
                                                  value: "Stand",
                                                });
                                              }
                                              if (
                                                gameState?.mode === "auto" ||
                                                gameState?.mode === "manual"
                                              ) {
                                                sendWebSocketMessage({
                                                  action: "next_turn",
                                                  player_id: "player6",
                                                  hand_index: 0,
                                                });
                                                clearInsuranceForHand(
                                                  "player6",
                                                  0,
                                                  1
                                                );
                                              }
                                            }}
                                            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                                          >
                                            Stand
                                          </button>

                                        </>
                                      )}
                                  </div>
                                  {/* STATUS TEXT SPLIT 1 */}
                                  {gameState.players.player6.split1[0]?.live_function_hand &&
                                    !["insurence", "surrender"].includes(
                                      gameState.players.player6.split1[0].live_function_hand
                                    ) && (
                                      <div className="absolute top-[50%] left-[50%] transform -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none">
                                        <span className="text-5xl font-extrabold text-white drop-shadow-[0_4px_4px_rgba(0,0,0,0.8)] animate-pulse tracking-widest bg-black/60 px-6 py-3 rounded-xl border-4 border-yellow-500 backdrop-blur-sm">
                                          {gameState.players.player6.split1[0].live_function_hand.toUpperCase()}
                                        </span>
                                      </div>
                                    )}
                                </div>
                              </div>
                            )}

                          {/* Split2 Hand (auto mode: show if cards exist) */}
                          {gameState.mode !== "manual" &&
                            gameState.players.player6.split2[0]?.cards?.length >
                            0 && (
                              <div className="mt-4">
                                <div
                                  className={`rounded-xl p-4 relative ${getHandBoxColor(
                                    isHandSelected(
                                      gameState,
                                      "player6",
                                      0,
                                      2
                                    ) &&
                                    gameState?.current_player === "player6",
                                    gameState.players.player6.status === 1,
                                    gameState.players.player6.split2[0]?.result
                                  )}`}
                                >
                                  <div className="text-left mb-1">
                                    <div
                                      className={`text-lg font-medium text-black`}
                                    >
                                      Split Hand 2
                                    </div>
                                  </div>

                                  <div className="flex justify-center items-center gap-4 mb-4">
                                    {gameState.players.player6.split2[0].cards.map(
                                      (card, index) => (
                                        <div
                                          key={index}
                                          className="relative w-36 h-52 transform hover:scale-110 transition-transform duration-200 group"
                                        >
                                          <img
                                            src={`/cards/${card}.png`}
                                            alt={card}
                                            className="w-full h-full object-contain"
                                            onError={(e) => {
                                              const target =
                                                e.target as HTMLImageElement;
                                              target.src = "/cards/back.png";
                                            }}
                                          />
                                        </div>
                                      )
                                    )}
                                    {[
                                      ...Array(
                                        Math.max(
                                          0,
                                          2 -
                                          (gameState.players.player6.split2[0]
                                            .cards.length ?? 0)
                                        )
                                      ),
                                    ].map((_, index) => (
                                      <div
                                        key={`empty-${index}`}
                                        className="w-36 h-52 border-2 border-dashed border-gray-400 rounded-lg flex items-center justify-center bg-gray-800/50"
                                      />
                                    ))}
                                  </div>

                                  <div className="absolute top-[93%] left-[43%] text-center">
                                    <div className="inline-block bg-[#911606] px-3 py-1 rounded-full text-sm font-bold text-[#d4af37] border-2 border-[#d4af37]">
                                      Total:{" "}
                                      {gameState.players.player6.split2[0]
                                        .total ?? 0}
                                    </div>
                                  </div>

                                  {/* Split2 Hand Action Buttons for Player 6 */}
                                  <div className="flex justify-center gap-2 flex-wrap mt-8">
                                    {gameState?.round_number !== 0 &&
                                      isHandSelected(
                                        gameState,
                                        "player6",
                                        0,
                                        2
                                      ) &&
                                      gameState?.current_player === "player6" &&
                                      gameState.players.player6.split2[0]?.cards
                                        ?.length === 2 &&
                                      canSplit(
                                        gameState.players.player6.split2[0]
                                          .cards
                                      ) &&
                                      gameState.players.player6.split2[0]
                                        .status === "playing" &&
                                      !gameState.players.player6.split2[0]?.live_function_hand &&
                                      (gameState.players.player6
                                        .split1_status === 0 ||
                                        gameState.players.player6
                                          .split2_status === 0) && (
                                        <button
                                          onClick={() => {
                                            if (gameState?.mode === "live") {
                                              sendWebSocketMessage({
                                                action:
                                                  "set_live_function_hand",
                                                player_id: "player6",
                                                split_level: 2,
                                                hand_index: 0,
                                                value: "Split",
                                              });
                                            }
                                            if (
                                              gameState?.mode === "auto" ||
                                              gameState?.mode === "manual"
                                            ) {
                                              sendWebSocketMessage({
                                                action: "split_player_auto",
                                                player_id: "player6",
                                              });
                                            }
                                          }}
                                          className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 transition-colors"
                                        >
                                          Split
                                        </button>
                                      )}

                                    {gameState?.round_number !== 0 &&
                                      isHandSelected(
                                        gameState,
                                        "player6",
                                        0,
                                        2
                                      ) &&
                                      !gameState.players.player6.split2[0]?.live_function_hand &&
                                      gameState?.current_player ===
                                      "player6" && (
                                        <>
                                          {gameState?.dealer
                                            ?.cards?.[0]?.[0] === "A" &&
                                            !insuranceState[`player6_0_2`] &&
                                            !gameState.players.player6.split2[0]
                                              .insurence &&
                                            gameState.players.player6
                                              .split1_status === 0 &&
                                            gameState.players.player6
                                              .split2_status === 0 &&
                                            gameState.players.player6.split2[0]
                                              ?.cards?.length === 2 &&
                                            gameState.players.player6
                                              .insurence !== 1 && (
                                              <button
                                                onClick={() => {
                                                  if (
                                                    gameState?.mode ===
                                                    "auto" ||
                                                    gameState?.mode === "manual"
                                                  ) {
                                                    handleInsurance("player6");
                                                  }
                                                }}
                                                className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors"
                                              >
                                                Insurance
                                              </button>
                                            )}
                                          <button
                                            onClick={() => {
                                              if (gameState?.mode === "live") {
                                                sendWebSocketMessage({
                                                  action:
                                                    "set_live_function_hand",
                                                  player_id: "player6",
                                                  split_level: 2,
                                                  hand_index: 0,
                                                  value: "Hit",
                                                });
                                              }
                                              if (
                                                gameState?.mode === "auto" ||
                                                gameState?.mode === "manual"
                                              ) {
                                                sendWebSocketMessage({
                                                  action: "hit_player",
                                                  player_id: "player6",
                                                  hand_index: 0,
                                                });
                                                clearInsuranceForHand(
                                                  "player6",
                                                  0,
                                                  2
                                                );
                                              }
                                            }}
                                            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
                                          >
                                            Hit
                                          </button>
                                          {gameState?.players?.player6
                                            ?.split2?.[0]?.cards?.length ===
                                            2 && (
                                              <button
                                                onClick={() => {
                                                  if (
                                                    gameState?.mode === "live"
                                                  ) {
                                                    sendWebSocketMessage({
                                                      action:
                                                        "set_live_function_hand",
                                                      player_id: "player6",
                                                      split_level: 2,
                                                      hand_index: 0,
                                                      value: "Double",
                                                    });
                                                  }
                                                  if (
                                                    gameState?.mode === "auto" ||
                                                    gameState?.mode === "manual"
                                                  ) {
                                                    sendWebSocketMessage({
                                                      action: "double_player",
                                                      player_id: "player6",
                                                      hand_index: 0,
                                                    });
                                                    clearInsuranceForHand(
                                                      "player6",
                                                      0,
                                                      2
                                                    );
                                                  }
                                                }}
                                                className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 transition-colors"
                                              >
                                                Double
                                              </button>
                                            )}
                                          <button
                                            onClick={() => {
                                              if (gameState?.mode === "live") {
                                                sendWebSocketMessage({
                                                  action:
                                                    "set_live_function_hand",
                                                  player_id: "player6",
                                                  split_level: 2,
                                                  hand_index: 0,
                                                  value: "Stand",
                                                });
                                              }
                                              if (
                                                gameState?.mode === "auto" ||
                                                gameState?.mode === "manual"
                                              ) {
                                                sendWebSocketMessage({
                                                  action: "next_turn",
                                                  player_id: "player6",
                                                  hand_index: 0,
                                                });
                                                clearInsuranceForHand(
                                                  "player6",
                                                  0,
                                                  2
                                                );
                                              }
                                            }}
                                            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                                          >
                                            Stand
                                          </button>

                                        </>
                                      )}
                                  </div>
                                  {/* STATUS TEXT SPLIT 2 */}
                                  {gameState.players.player6.split2[0]?.live_function_hand &&
                                    !["insurence", "surrender"].includes(
                                      gameState.players.player6.split2[0].live_function_hand
                                    ) && (
                                      <div className="absolute top-[50%] left-[50%] transform -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none">
                                        <span className="text-5xl font-extrabold text-white drop-shadow-[0_4px_4px_rgba(0,0,0,0.8)] animate-pulse tracking-widest bg-black/60 px-6 py-3 rounded-xl border-4 border-yellow-500 backdrop-blur-sm">
                                          {gameState.players.player6.split2[0].live_function_hand.toUpperCase()}
                                        </span>
                                      </div>
                                    )}
                                </div>
                              </div>
                            )}
                        </div>
                      )}

                      {/* Next Button */}
                      {gameState.players.player6.status === 1 &&
                        gameState?.current_turn === "player" && (
                          <div className="mt-6 flex justify-end">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleNextTurn();
                              }}
                              className="px-6 py-2 bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white rounded-lg transition-all duration-300 transform hover:scale-105 shadow-lg flex items-center space-x-2 text-base"
                            >
                              <svg
                                className="w-5 h-5"
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
                              <span>Next Turn</span>
                            </button>
                          </div>
                        )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
          {/* Enhanced Popup Message */}
          {showPopup && (
            <div className="fixed top-8 left-1/2 transform -translate-x-1/2 z-50 animate-bounce">
              <div className="bg-gradient-to-r from-red-800 to-red-700 border border-red-600 text-white px-8 py-4 rounded-2xl shadow-2xl flex items-center space-x-3 backdrop-blur-xl">
                <div className="w-3 h-3 bg-gradient-to-r from-green-400 to-green-500 rounded-full animate-pulse"></div>
                <span className="font-medium text-lg">{popupMessage}</span>
              </div>
            </div>
          )}

          {/* Result Popup */}
          {showResultPopup && (
            <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 backdrop-blur-sm">
              <div className="bg-gradient-to-br from-green-900 via-green-800 to-emerald-900 border-4 border-yellow-400 text-white p-8 rounded-3xl shadow-2xl max-w-lg w-full mx-4 relative overflow-hidden">
                {/* Decorative corners */}
                <div className="absolute top-2 left-2 w-6 h-6 border-l-4 border-t-4 border-yellow-400 rounded-tl-lg"></div>
                <div className="absolute top-2 right-2 w-6 h-6 border-r-4 border-t-4 border-yellow-400 rounded-tr-lg"></div>
                <div className="absolute bottom-2 left-2 w-6 h-6 border-l-4 border-b-4 border-yellow-400 rounded-bl-lg"></div>
                <div className="absolute bottom-2 right-2 w-6 h-6 border-r-4 border-b-4 border-yellow-400 rounded-br-lg"></div>

                <div className="text-center relative z-10">
                  {/* Main result with dramatic styling */}
                  <div className="mb-6">
                    <div className="text-8xl mb-2 animate-bounce">
                      {playerResult === "win" && "🏆"}
                      {playerResult === "lose" && "💸"}
                      {playerResult === "tie" && "🤝"}
                      {playerResult === "surrender" && "🏳️"}
                    </div>
                    <h2 className="text-4xl font-bold mb-2 text-yellow-300 drop-shadow-lg tracking-wider">
                      {playerResult === "win" && "YOU WIN"}
                      {playerResult === "lose" && "YOU LOSE"}
                      {playerResult === "tie" && "PUSH"}
                      {playerResult === "surrender" && "SURRENDER"}
                    </h2>
                    <div className="text-xl text-yellow-100 opacity-90">
                      {playerResult === "win" && "Congratulations!"}
                      {playerResult === "lose" && "Better luck next time"}
                      {playerResult === "tie" && "Nobody wins this round"}
                      {playerResult === "surrender" &&
                        "You surrendered this hand"}
                    </div>
                  </div>

                  {/* Hand results with casino-style presentation */}
                  <div className="mb-6 space-y-3">
                    {(() => {
                      const player6Data = gameState?.players?.player6;
                      if (!player6Data) return null;
                      const handResults = [
                        {
                          label: "Main Hand",
                          result: player6Data.hands?.[0]?.result,
                          icon: "🎰",
                        },
                        {
                          label: "Split 1",
                          result: player6Data.split1?.[0]?.result,
                          icon: "🃏",
                        },
                        {
                          label: "Split 2",
                          result: player6Data.split2?.[0]?.result,
                          icon: "🎯",
                        },
                      ];

                      const getResultDisplay = (result: string) => {
                        switch (result) {
                          case "win":
                            return {
                              text: "WIN",
                              color: "text-green-300",
                              bg: "bg-green-700/30",
                            };
                          case "fail":
                          case "lose":
                            return {
                              text: "LOSE",
                              color: "text-red-300",
                              bg: "bg-red-700/30",
                            };
                          case "tie":
                            return {
                              text: "PUSH",
                              color: "text-yellow-300",
                              bg: "bg-yellow-700/30",
                            };
                          case "surrender":
                            return {
                              text: "SURRENDER",
                              color: "text-blue-300",
                              bg: "bg-blue-700/30",
                            };
                          default:
                            return null;
                        }
                      };

                      return handResults.map((hand, i) => {
                        if (!hand.result) return null;
                        const display = getResultDisplay(hand.result);
                        if (!display) return null;

                        return (
                          <div
                            key={i}
                            className={`flex items-center justify-between p-3 rounded-xl border-2 border-yellow-600/50 ${display.bg}`}
                          >
                            <div className="flex items-center gap-2">
                              <span className="text-2xl">{hand.icon}</span>
                              <span className="font-semibold text-lg">
                                {hand.label}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              {/* Insurance Badge - Only for Main Hand if insurance taken */}
                              {i === 0 && player6Data.insurence === 1 && (
                                <span className="px-2 py-0.5 bg-yellow-500/80 text-black text-xs font-bold rounded border border-yellow-400 uppercase tracking-wider">
                                  INSURED
                                </span>
                              )}
                              <span
                                className={`font-bold text-xl ${display.color} drop-shadow-md`}
                              >
                                {display.text}
                              </span>
                            </div>
                          </div>
                        );
                      });
                    })()}
                  </div>

                  {/* Action button with casino styling */}
                  <button
                    onClick={() => {
                      setShowResultPopup(false);
                      setResultPopupDismissed(true); // Set the dismissed flag
                    }}
                    className="bg-gradient-to-r from-yellow-500 via-yellow-600 to-yellow-700 hover:from-yellow-600 hover:via-yellow-700 hover:to-yellow-800 text-black px-8 py-4 rounded-2xl font-bold text-xl transition-all duration-300 transform hover:scale-105 shadow-lg border-2 border-yellow-300 hover:border-yellow-200 active:scale-95"
                  >
                    DEAL AGAIN
                  </button>
                </div>

                {/* Subtle pattern overlay */}
                <div className="absolute inset-0 opacity-10 bg-gradient-to-br from-transparent via-yellow-300/20 to-transparent pointer-events-none"></div>
              </div>
            </div>
          )}

          {/* Pair Type Popup */}
          {showPairPopup && (
            <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 backdrop-blur-sm">
              <div className="bg-gradient-to-br from-blue-900 via-blue-800 to-blue-700 border-4 border-blue-400 text-white p-8 rounded-3xl shadow-2xl max-w-lg w-full mx-4 relative overflow-hidden">
                {/* Decorative corners */}
                <div className="absolute top-2 left-2 w-6 h-6 border-l-4 border-t-4 border-blue-400 rounded-tl-lg"></div>
                <div className="absolute top-2 right-2 w-6 h-6 border-r-4 border-t-4 border-blue-400 rounded-tr-lg"></div>
                <div className="absolute bottom-2 left-2 w-6 h-6 border-l-4 border-b-4 border-blue-400 rounded-bl-lg"></div>
                <div className="absolute bottom-2 right-2 w-6 h-6 border-r-4 border-b-4 border-blue-400 rounded-br-lg"></div>

                <div className="text-center relative z-10">
                  {/* Main content with dramatic styling */}
                  <div className="mb-6">
                    <div className="text-8xl mb-4 animate-bounce">🎯</div>
                    <h2 className="text-4xl font-bold mb-4 text-blue-200 drop-shadow-lg tracking-wider">
                      CONGRATULATION!🎊
                    </h2>
                    <div className="text-3xl font-bold text-yellow-300 mb-4">
                      {pairType}
                    </div>
                    <div className="text-xl text-blue-100 opacity-90">
                      Congratulations on your pair!
                    </div>
                  </div>

                  {/* OK Button */}
                  <button
                    onClick={() => setShowPairPopup(false)}
                    className="px-8 py-3 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white text-xl font-bold rounded-xl transition-all duration-300 transform hover:scale-105 shadow-lg border-2 border-blue-300"
                  >
                    OK
                  </button>
                </div>
              </div>
            </div>
          )}
          {/* Bottom disclaimer - Marquee */}
          <div className="fixed bottom-0 w-full text-xl py-1 overflow-hidden">
            <div className="whitespace-nowrap animate-marquee">
              THIS IS AN ELECTRONIC GAME INCASE OF ANY GRIEVANCES THE MANAGEMENT
              DECISION WILL BE FINAL &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; •
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; THIS IS AN ELECTRONIC GAME INCASE
              OF ANY GRIEVANCES THE MANAGEMENT DECISION WILL BE FINAL
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; • &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
              THIS IS AN ELECTRONIC GAME INCASE OF ANY GRIEVANCES THE MANAGEMENT
              DECISION WILL BE FINAL &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; •
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; THIS IS AN ELECTRONIC GAME INCASE
              OF ANY GRIEVANCES THE MANAGEMENT DECISION WILL BE FINAL
            </div>
          </div>
        </div>
      ) : (
        <div className="fixed inset-0 w-screen h-screen flex justify-center items-center z-50">
          <video
            autoPlay
            loop
            muted
            className="absolute inset-0 w-full h-full object-cover"
          >
            <source src="/assets/ocean7vid.mp4" type="video/mp4" />
            Your browser does not support the video tag.
          </video>
        </div>
      )
      }
    </div >
  );
};

export default GameMenu;
