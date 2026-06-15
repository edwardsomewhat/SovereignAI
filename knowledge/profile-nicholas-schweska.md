# Nicholas "Nick" Schweska — Complete Research Profile
> Compiled: June 14, 2026 | Source: Public web data, Combustion Syndicate site, social media, public records, internal infrastructure

---

## I. PERSONAL IDENTITY

- **Full Name:** Nicholas Schweska (goes by "Nick")
- **Alias/Brand:** edwardsomewhat / edwardsomewhat glass / edwardsomewhat1of1
- **Age:** 39 (born ~1987)
- **Location:** 212 3rd St, Colona, IL 61241 (since 2018)
- **Previous Locations:** Silvis, IL (2007–2020), Davenport, IA (2015–2019)
- **Marital Status:** Married to Ellie Davis (November 15, 2025)
- **Relationship Timeline:**
  - Met Fall 2022
  - Became official November 15, 2022
  - Proposed December 30, 2024 at Kew Gardens, London
  - Married November 15, 2025 (exactly 3 years after becoming official)
  - Venue: Rockwell on the River, Chicago, IL
  - Registries: Amazon, Crate & Barrel, Anthropologie
- **Family:** Deborah L Schweska (60), Dustin P Schweska (38), John Richard Schweska (58), Amber Lynn Schweska (37), Mary Etta Shipley (50)

---

## II. GLASS ART — "edwardsomewhat glass"

### Business Identity
- **Brand:** edwardsomewhat glass
- **NAICS Code:** 327212 (Other Pressed and Blown Glass and Glassware Manufacturing)
- **PPP Loan:** $3,027 (January 2021, self-employed, 1 job)
- **Specialization:** Functional glass art — handcrafted pipes, rigs, pendants, sherlocks, spoons
- **Glass Manufacturers:** NorthStar Glass, Schott
- **Co-Collective:** Combustion Syndicate (with Fatman + Sergio)

### Artistic Philosophy
> "Form and function are the highest expression of art, so I make useful items, of art, and teach this dying craft."
> — People's Artist submission, benefiting The Art of Elysium (placed 37th)

### Techniques Mastered
- Donut shaping | Downstem work | Gong joint pressing
- Frit work (Yellow Frit, Double Amber Purple)
- Fuming (Silver Fume)
- Implosion | Encalmo | Encolmo
- Wig wag | Blowout | Sculpture

### Catalogue (Available on combustionsyndicate.com)

| Piece | Price | Materials | Style |
|-------|-------|-----------|-------|
| Suspiciously Convenient 10mm Rig | $80 | Yellow Frit, Silver Fume | 10mm Rig |
| Purp Looker | $60 | Double Amber Purple Frit | Pendy Pipe |
| Stargazer Galaxy Sherlock | $125 | Stargazer V2, Galaxy | Sherlock |
| 2 Face Wig Wag Spoon | $40 | NorthStar | Spoon |
| Horned spoon dbl amb | $20 | Double Amber Frit | Spoon |
| Yellow Sax | $50 | NorthStar | — |
| Purple Mountain Galaxy Pendy Pipe | $75 | Galaxy, Purple Mountain, Stargazer V2 | Pendy Pipe |

---

## III. COMBUSTION SYNDICATE

### The Collective
- **Domain:** combustionsyndicate.com
- **Co-Founders:** Nick Schweska, "Fatman", Sergio
- **Tagline:** "We are Born Here"
- **Mission Statement:** "Everything you see here is American Made — From the Art to the Website, To the bare metal hardware it lives on. We made it all. We will continue to make it all."

### Core Declaration
> "We are the Combustion Syndicate, American Artists, Producing American Products, in America. We have not been funded by, nor do we sell data of any sort to any Corporate Interests."

### Website Architecture
- **Framework:** Next.js (React, Turbopack)
- **CMS:** Directus (admin.combustionsyndicate.com)
- **Hosting:** Self-hosted on bare metal (CS Webs VM at 100.71.6.98)
- **Email:** Purelymail (12 addresses @combustionsyndicate.com)
- **Pages:** Home, Shop, V2G (Vision to Glass), Team, Ethos, SovereignAI, Community, Workshop, Support
- **Features:** Shopping cart, member portal (/portal), search, newsletter signup
- **Dominant Aesthetic:** Dark theme, neon pink/cyan/purple gradient palette, "cyberpunk glass studio" vibe

### Email Infrastructure (Purelymail)
edwardsomewhat@purelymail.com (personal)
support@ | info@ | sales@ | wholesale@ | join@ | workshop@ | book@ | SovereignAI@ | FatEd@ | Fatman@ | edwardsomewhat@ | Avacado@ — all @combustionsyndicate.com

### Future Plans
- Kickstarter campaign planned
- Glass art revenue funds SovereignAI R&D

---

## IV. SOVEREIGNAI — The Technology Operation

### Infrastructure
- **Scale:** 22-node distributed compute network
- **Network:** Tailscale mesh VPN
- **Hypervisor:** Proxmox
- **Containerization:** Docker

### Hardware Fleet

| Node | Hardware | Role | Key Specs |
|------|----------|------|-----------|
| HP Z8 G4 ("The Conch") | Proxmox host | VM orchestration | Dual Xeon 5218 |
| 3090 Rig | Custom | Heavy GPU compute | 7950X3D, RTX 3090 (24GB VRAM), 64GB RAM |
| P5000 Node ("hq-ai") | Custom | Secondary GPU compute | Quadro P5000 (16GB VRAM) |
| Jetson Orin Nano Super | NVIDIA | Edge AI | 8GB, Google Coral TPU |
| Sovereign | VM | Primary AI agent host | — |
| Charlotte | LXC | n8n automation | Port :5678 |
| Sage | VM | Partner's agent instance | XFCE desktop, RustDesk |
| CS Webs | VM | Combustion Syndicate website | Next.js + Directus |
| Masogany | Windows PC | Nick's desktop | Steel (3.8TB), Leather drives |
| Gaming PCs (multiple) | — | Overflow compute | Distributed inference/training |

### AI Workloads
- **vLLM:** LLM inference serving (3090 Rig)
- **ComfyUI (×2):** Image generation (3090 Rig + P5000 Node)
- **Ollama:** Local LLM serving (P5000 Node, Nano)
- **Qwen3 TTS (×2):** Text-to-speech (3090 Rig + P5000 Node)
- **n8n:** Automation workflows (Charlotte)
- **Honcho:** Agent memory/personality backend (Sovereign)
- **Syncthing:** File sync across nodes

### Workload Routing Priority
1. RTX 3090: vLLM > ComfyUI > TTS
2. Quadro P5000: Ollama → ComfyUI → TTS
3. Jetson Orin Nano + Coral: Edge inference only
4. Gaming PCs: Overflow/batch

### Active Projects
- **Macho Man Translator:** Fine-tuning Qwen 2.5 1.5B → GGUF for $0.99 phone app (zero IAP)
- **Sovereign Cloning Protocol:** Reproducible AI agent VM deployment
- **Combustion Syndicate Website:** Live Next.js e-commerce with Directus CMS
- **Pi Agent:** Self-extending ComfyUI workflow builder

### Philosophy
- Anti-SaaS / Anti-subscription / Anti-rent-seeking
- Self-hosted, owned metal, open-source integrations
- $0.99 apps with zero in-app purchases as a statement
- "AI is a neutral tool — can build or destroy, like a hammer"

---

## V. DIGITAL FOOTPRINT

| Platform | Handle/URL | Stats |
|----------|------------|-------|
| Facebook (personal) | facebook.com/edwardsomewhat.glass | 1,226 likes, "Digital creator" |
| Facebook (business) | facebook.com/edwardsomewhat | 293 likes, glass inventory archive |
| Instagram | instagram.com/edwardsomewhatglass | 592 followers, 158 posts |
| LinkedIn | linkedin.com/in/nick-schweska-959790251 | 4 connections |
| Pinterest | pinterest.com/edwardsomewhat1of1 | 290 pins, 5 boards |
| The Knot | Wedding website | Nov 15, 2025 |
| People's Artist | peoplesartist.org/2026/nicholas-schwes-3ZM8 | Placed 37th |

### Pinterest Boards
- Glass art (9 pins)
- Pipe ideas (57 pins)
- Woodworking (51 pins)
- DIY Arcade Cabinet (24 pins)
- Cyber deck ideas (5 pins)
- iRacing rig (2 pins)
- Kids room (26 pins)
- Home fix (5 pins)
- Classy home organizer (9 pins)

---

## VI. PERSONAL TRAITS & INTERESTS

### Personality
- **Creative Style:** "Explosive creative energy" / "bird brain" — multi-threaded thinker
- **Ethos:** "Risk it: build now, refine later"
- **Technical Preference:** Direct tool calling over agent frameworks
- **Competitive:** Loves sports, sports betting, fantasy football (Dallas Cowboys loyalist)
- **Demonstration-oriented:** Wants real-time tool calls, agent-to-agent interaction

### Hobbies & Interests
- Woodworking (51 Pinterest pins)
- Cyberdecks / custom computing builds
- DIY arcade cabinet building
- iRacing / sim racing
- Chicago Cubs baseball
- Golf
- Glassblowing (obviously — the career + the art)

### Operating Style
- Dense, multi-thread messages — ALL points must be acknowledged
- Values agent sovereignty — wants AI to make decisions, own calls
- Anti-SaaS, anti-subscription, anti-corporate rent-seeking
- Believes glass art funds the tech R&D pipeline

---

## VII. KEY QUOTES

1. "Form and function are the highest expression of art, so I make useful items, of art, and teach this dying craft."
2. "We have not been funded by, nor do we sell data of any sort to any Corporate Interests."
3. "Everything you see here is American Made — From the Art to the Website, To the bare metal hardware it lives on."
4. "We are the Combustion Syndicate, American Artists, Producing American Products, in America."

---

*Profile compiled from: combustionsyndicate.com, federalpay.org, peoplesartist.org, instantcheckmate.com, theknot.com, Facebook, Instagram, LinkedIn, Pinterest, and internal SovereignAI infrastructure documentation.*
