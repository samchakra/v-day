# app.py
import re
import streamlit as st
import streamlit.components.v1 as components

# ----------------------------
# Config
# ----------------------------
st.set_page_config(
    page_title="Valentine Mini Wordle",
    page_icon="❤️",
    layout="centered",
)

ANSWERS = ["FLIRT", "SWEET", "AMOUR", "HEART"]
INTER_ROUND_NOTES = [
    "Nice. Keep going.",    # after FLIRT
    "You're on pace.",       # after SWEET
    "Alright… last round.",  # after AMOUR
    "Look up.",              # after HEART (before question screen)
]

# Optional: allow only these as "valid guess" words.
# For a true Wordle you'd have a large dictionary; keeping minimal for your use-case.
VALID_GUESSES = set(ANSWERS + ["LATER", "TEARS", "SMILE", "ROSES", "ADORE", "LOVER", "ANGEL", "KISSES"])
STRICT_VALIDATION = False  # set True if you want to reject guesses not in VALID_GUESSES

# ----------------------------
# Minimal mobile-first styles
# ----------------------------
st.markdown(
    """
<style>
/* Keep it clean + mobile-first */
.main .block-container {
  max-width: 420px;
  padding-top: 16px;
  padding-bottom: 28px;
}

/* Hide Streamlit menu/footer for a more app-like feel */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Title */
.h1 {
  font-size: 22px;
  font-weight: 700;
  margin: 8px 0 6px 0;
  text-align: center;
}

/* Tiles */
.grid {
  display: grid;
  gap: 8px;
  margin: 14px 0 16px 0;
}
.row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}
.tile {
  border: 1.6px solid #d0d0d0;
  border-radius: 10px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 1px;
  user-select: none;
}

.tile.empty { background: #ffffff; }
.tile.absent { background: #e9ecef; border-color: #e9ecef; color: #111; }
.tile.present { background: #fff3bf; border-color: #fff3bf; color: #111; }
.tile.correct { background: #b7f0c1; border-color: #b7f0c1; color: #111; }

/* Subtle win pop */
@keyframes pop {
  0% { transform: scale(1); }
  60% { transform: scale(1.04); }
  100% { transform: scale(1); }
}
.win-pop { animation: pop 220ms ease-out; }

/* Buttons spacing on mobile */
.stButton>button {
  width: 100%;
  border-radius: 12px;
  padding: 12px 14px;
  font-weight: 700;
}

/* Small helper text */
.small {
  font-size: 13px;
  color: #666;
  text-align: center;
  margin-top: 6px;
}

/* Centered note card */
.note {
  border: 1px solid #eee;
  border-radius: 14px;
  padding: 14px 14px;
  background: #fff;
  text-align: center;
  font-size: 15px;
}

/* Final screen */
.finalQ {
  text-align: center;
  font-size: 26px;
  font-weight: 800;
  margin: 20px 0 16px 0;
}
</style>
""",
    unsafe_allow_html=True,
)

# ----------------------------
# Helpers
# ----------------------------
def init_state():
    if "round_idx" not in st.session_state:
        st.session_state.round_idx = 0  # 0..len(ANSWERS)-1, then final question
    if "guesses" not in st.session_state:
        # list of rounds, each round is list of guesses (strings)
        st.session_state.guesses = [[] for _ in ANSWERS]
    if "statuses" not in st.session_state:
        # parallel structure: list of rounds, each round: list of status rows, each status row: list of 5 strings
        st.session_state.statuses = [[] for _ in ANSWERS]
    if "round_solved" not in st.session_state:
        st.session_state.round_solved = [False for _ in ANSWERS]
    if "show_note" not in st.session_state:
        st.session_state.show_note = False
    if "final_choice" not in st.session_state:
        st.session_state.final_choice = None  # "YES" / "YESSS"
    if "win_pulse" not in st.session_state:
        st.session_state.win_pulse = False  # triggers subtle animation
    if "input_key" not in st.session_state:
        st.session_state.input_key = 0  # used to reset input


def score_guess(guess: str, answer: str):
    """
    Wordle scoring:
    correct (green), present (yellow), absent (gray)
    Handles repeats properly.
    """
    guess = guess.upper()
    answer = answer.upper()

    status = ["absent"] * 5
    answer_counts = {}

    # First pass: mark correct
    for i, (g, a) in enumerate(zip(guess, answer)):
        if g == a:
            status[i] = "correct"
        else:
            answer_counts[a] = answer_counts.get(a, 0) + 1

    # Second pass: mark present
    for i, g in enumerate(guess):
        if status[i] == "correct":
            continue
        if answer_counts.get(g, 0) > 0:
            status[i] = "present"
            answer_counts[g] -= 1

    return status


def is_valid_guess(s: str):
    s = s.strip().upper()
    if not re.fullmatch(r"[A-Z]{5}", s):
        return False, "Enter exactly 5 letters."
    if STRICT_VALIDATION and s not in VALID_GUESSES:
        return False, "Not in the word list."
    return True, ""


def render_grid(round_idx: int):
    """
    Render a 6-row Wordle grid. Past guesses are colored.
    Empty rows show blank tiles.
    """
    guesses = st.session_state.guesses[round_idx]
    statuses = st.session_state.statuses[round_idx]

    # Determine if we should apply a subtle pop animation (only on win)
    win_class = "win-pop" if st.session_state.win_pulse else ""

    html = ['<div class="grid">']
    for r in range(6):
        html.append('<div class="row">')
        if r < len(guesses):
            g = guesses[r]
            st_row = statuses[r]
            for i in range(5):
                letter = g[i]
                cls = st_row[i]
                html.append(f'<div class="tile {cls} {win_class}">{letter}</div>')
        else:
            for _ in range(5):
                html.append('<div class="tile empty"></div>')
        html.append("</div>")
    html.append("</div>")

    st.markdown("".join(html), unsafe_allow_html=True)

    # Reset pulse after render so it only pops once
    st.session_state.win_pulse = False


def reset_all():
    for k in list(st.session_state.keys()):
        del st.session_state[k]


# ----------------------------
# App
# ----------------------------
init_state()

# Optional reset (handy while testing)
with st.expander("Debug / reset", expanded=False):
    if st.button("Reset game"):
        reset_all()
        st.rerun()

# If all rounds solved, go to final
all_solved = all(st.session_state.round_solved)
if all_solved and st.session_state.round_idx < len(ANSWERS):
    st.session_state.round_idx = len(ANSWERS)

# Final question screen
if st.session_state.round_idx >= len(ANSWERS):
    st.markdown('<div class="finalQ">Will you be my Valentine?</div>', unsafe_allow_html=True)

    # One YES button (real Streamlit button)
    if st.button("YES"):
        st.session_state.final_choice = "YES"

    # Fake "No 😢" that disintegrates slowly on tap/click
    components.html(
    """
    <div style="
        margin-top: 14px;
        display: flex;
        justify-content: center;
    ">
      <button id="noBtn" type="button" style="
          width: 100%;
          max-width: 340px;
          padding: 12px 14px;
          border-radius: 12px;
          border: 1px solid #f0f0f0;
          background: #fafafa;
          font-weight: 700;
          cursor: pointer;
          touch-action: manipulation;
      ">No 😢</button>
    </div>

    <style>
      @keyframes dustFade {
        0%   { opacity: 1; filter: blur(0px); transform: translateY(0px); }
        30%  { opacity: 0.95; filter: blur(0.3px); transform: translateY(-1px); }
        60%  { opacity: 0.65; filter: blur(1.6px); transform: translateY(-7px); }
        85%  { opacity: 0.25; filter: blur(3.0px); transform: translateY(-14px); }
        100% { opacity: 0; filter: blur(4.5px); transform: translateY(-22px); }
      }

      /* Slower "dusting" */
      #noBtn.dusting {
        position: relative;
        animation: dustFade 5.8s ease-in-out forwards;
        pointer-events: none;
      }

      #noBtn.dusting::after {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: 12px;
        background-image: radial-gradient(rgba(0,0,0,0.10) 1px, transparent 1px);
        background-size: 11px 11px;
        opacity: 0.20;
        animation: dustFade 5.8s ease-in-out forwards;
        mix-blend-mode: multiply;
      }
    </style>

    <script>
      (function () {
        const btn = document.getElementById("noBtn");
        let started = false;

        function startDust(e) {
          if (started) return;
          started = true;

          btn.classList.add("dusting");

          // Remove from layout after animation ends
          setTimeout(() => {
            btn.style.display = "none";
          }, 5900);

          e.preventDefault();
          e.stopPropagation();
        }

        ["pointerdown","touchstart","mousedown","click"].forEach(evt => {
          btn.addEventListener(evt, startDust, { passive: false });
        });
      })();
    </script>
    """,
    height=95,
)


    if st.session_state.final_choice:
        st.markdown(
            """
<div class="note" style="margin-top:16px;">
  ❤️ <b>YES</b> ❤️
  <div class="small" style="margin-top:8px;">Best answer.</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.balloons()

    st.stop()



# Round play screen
round_idx = st.session_state.round_idx
answer = ANSWERS[round_idx]
round_title = f"Round {round_idx + 1} of {len(ANSWERS)}"
st.markdown(f'<div class="h1">{round_title}</div>', unsafe_allow_html=True)
st.markdown('<div class="small">Guess the 5-letter word.</div>', unsafe_allow_html=True)

render_grid(round_idx)

# If solved, show note + Next button
if st.session_state.round_solved[round_idx]:
    note = INTER_ROUND_NOTES[round_idx]
    st.markdown(f'<div class="note">{note}</div>', unsafe_allow_html=True)
    if st.button("Next round"):
        st.session_state.show_note = False
        st.session_state.round_idx += 1
        st.session_state.input_key += 1
        st.rerun()
    st.stop()

# If failed (6 guesses used)
if len(st.session_state.guesses[round_idx]) >= 6:
    st.markdown(
        f'<div class="note">Out of guesses. The word was <b>{answer}</b>.</div>',
        unsafe_allow_html=True,
    )
    if st.button("Try again"):
        # reset only current round
        st.session_state.guesses[round_idx] = []
        st.session_state.statuses[round_idx] = []
        st.session_state.round_solved[round_idx] = False
        st.session_state.input_key += 1
        st.rerun()
    st.stop()

# Guess input (mobile-friendly: single text input)
guess = st.text_input(
    "Your guess",
    value="",
    max_chars=5,
    key=f"guess_input_{st.session_state.input_key}",
    placeholder="Type 5 letters…",
    label_visibility="collapsed",
)

submit = st.button("Submit guess")

if submit:
    g = guess.strip().upper()

    ok, msg = is_valid_guess(g)
    if not ok:
        st.error(msg)
        st.stop()

    # Score and store
    st.session_state.guesses[round_idx].append(g)
    st.session_state.statuses[round_idx].append(score_guess(g, answer))

    # Win?
    if g == answer:
        st.session_state.round_solved[round_idx] = True
        st.session_state.win_pulse = True  # trigger subtle pop on next render
        st.session_state.input_key += 1
        st.rerun()

    # Otherwise continue
    st.session_state.input_key += 1
    st.rerun()
