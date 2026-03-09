# Whisperchain Game (Full stack learning)
**A full-stack experimental game to learn backend, frontend, database, FlaskAPI in a Linux environment.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![JavaScript](https://img.shields.io/badge/javascript-ES6+-yellow.svg)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![HTML5](https://img.shields.io/badge/html5-orange.svg)](https://developer.mozilla.org/en-US/docs/Web/HTML)
[![CSS3](https://img.shields.io/badge/css3-blueviolet.svg)](https://developer.mozilla.org/en-US/docs/Web/CSS)
[![SQL](https://img.shields.io/badge/SQL-lightgrey.svg)](https://en.wikipedia.org/wiki/SQL)
[![Linux](https://img.shields.io/badge/linux-FCC624?logo=linux&logoColor=black)](https://www.kernel.org/)
[![Status: Experimental](https://img.shields.io/badge/status-experimental-orange.svg)]()

---

## What It Was For
Whisperchain is an online multiplayer-first project meant to teach full-stack development, production, and deployment.

## It will be available for the next 27 days (from today 9 March 2026 as it is using a Railway free server)
You may try it through the following link:
[game-whisperchain on Railway](https://game-whisperchain-production.up.railway.app)

---


# Installation

```bash
# 1. Clone the repo
git clone https://github.com/LogoASeguir/game-whisperchain
cd game-whisperchain

# 2. Install dependencies
pip install -r requirements.txt
```

# 3. Run (Docker recommended)
```bash
docker-compose up --build
```

## Project Architecture ##
```
---------------------------------------------------------------
backend/         # Python game engine and server API connection
frontend/        # HTML, CSS, JS game UI
db/              # Database schema & backups
Dockerfile       # Container setup
docker-compose.yml
---------------------------------------------------------------
```

## Project Status
Whisperchain will end its course here, as there is more to be learned.
```
Future updates could include:
- Community-based library for words approved through contest voting
- Background redesign (sideways scrolling word bank to guide new players)
- Better UX with sound and a community server (Discord)
- Game design tweaks (scoring system, more game modes)
- Exporting game summaries automatically near database limit to prevent collapse.
```

## Philosophy
This project was built with AI tools as a development accelerator to better understand SQL, Python, and API connections, while learning Linux navigation.  
Python is becoming clearer with each project.  
The frontend-backend relationship is now much more understandable.  
No deep dive into frontend languages yet, but a general grasp is in place!

## Project Considerations
```
- Socket layer added to control data flow before DB
- Rooms, and usernames auto-deleted to preserve space and the purpose of the experience. Game summaries are permanent.
- DB hosted on Supabase, server on Railway
- Explored HTTP vs HTTPS basics
- Frontend-backend-data separation maintained
```
## Author
Built by [Renato Pedrosa]

Part of a growing knowledge personal toolkit.




