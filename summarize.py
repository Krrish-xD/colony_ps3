import sys
import os

with open("all_content.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Define the sections
sections = {
    "Overview": "The current war between Iran and Israel (also involving the US) has reached its 27th day (as of March 26-27, 2026), marking a significant escalation in the Middle East. ",
    "Key Events (March 23-27, 2026)": "",
    "Diplomatic Efforts & Ceasefire Proposals": "",
    "Impact on Global Trade & Oil Prices": "",
    "Status of India and Its Nationals": ""
}

# Overview
sections["Overview"] += "Multiple flashpoints have lit up across Iran, Israel, and Lebanon, and drone/missile incidents were reported from the UAE, Kuwait, and Saudi Arabia. US President Donald Trump is actively involved in the situation, issuing ultimatums and engaging in ceasefire talks, although these efforts have faced hurdles."

# Key Events
sections["Key Events (March 23-27, 2026)"] = """
- Iran fired a fresh broadside of missiles at Israel on March 24, causing damage and injuries in Tel Aviv.
- Israel says its attacks on Iran "will escalate and expand," targeting military-industrial sites and weapons production infrastructure. Israel's defense minister confirmed this in response to waves of Iranian missiles.
- Iran state media reports that nuclear facilities have been targeted, but there is "no risk of contamination."
- Israel claimed to have killed the Islamic Revolutionary Guard Corps (IRGC) Navy commander, Alireza Tangsiri, in a strike in Bandar Abbas. He was reportedly "responsible for the closure of the Strait of Hormuz."
- The deadly bombing of an Iranian school (Shajareh Tayyebeh Elementary School in Minab) drew condemnation, with Iran describing it as a "war crime" by the United States.
- The UAE intercepted 15 ballistic missiles and 11 drones launched from Iran on March 26.
- A marine drone hit a Turkish crude oil tanker in the Black Sea near Istanbul’s Bosphorus Strait.
"""

# Diplomatic Efforts
sections["Diplomatic Efforts & Ceasefire Proposals"] = """
- The US sent Iran a 15-point peace plan to end the conflict. Measures included easing sanctions, scaling back Iran's nuclear program, imposing limits on its missile capabilities, and reopening the Strait of Hormuz.
- Iran rejected the US proposal as "one-sided" and put forward its own counteroffer on state television, calling for an end to the targeting of its officials, guarantees against future attacks, compensation for war damages, a cessation of hostilities, and recognition of its sovereignty over the Strait of Hormuz.
- Trump said he is uncertain about sticking to a five-day delay for strikes on Iran energy sites, but later extended the deadline to April 6, citing ongoing talks that are "going very well."
- Trump also suggested that Iran let ten oil tankers through the Strait of Hormuz to show goodwill.
- Pakistan and Egypt are reportedly shuttling messages between Iran and the US.
"""

# Impact on Global Trade
sections["Impact on Global Trade & Oil Prices"] = """
- The US, Israel attack on Iran has ignited the "worst trade rupture in 80 years."
- Iran has started to formalize its chokehold on the Strait of Hormuz with a "toll booth" regime, although a parliament member says the toll fee proposal will be reviewed next week.
- Oil prices jumped over 4% amid the conflict and the Strait of Hormuz curbs.
- Middle East airlines have scaled back operations.
- Maersk is maintaining food and medicine supply lines in the Gulf.
"""

# India Status
sections["Status of India and Its Nationals"] = """
- Indian Prime Minister Narendra Modi chaired a meeting with the Chief Ministers of all States to review their preparedness and plans for the West Asia conflict.
- The Indian government confirmed the tragic death of one Indian national in Abu Dhabi due to missile interception debris, while another was injured.
- The Indian government assured that "India's petroleum and LPG supply situation is fully secure," with no shortage of petrol, diesel, or LPG anywhere in India.
- The Indian embassy condoled the demise of the Indian national in Abu Dhabi.
- NTA provided an update for Indian expat students in Dubai, Kuwait, and Bahrain.
"""

with open("iran_israel_war_report.md", "w", encoding="utf-8") as f:
    f.write("# Comprehensive Report on the Iran-Israel War (Status as of March 26-27, 2026)\n\n")
    for title, content in sections.items():
        f.write(f"## {title}\n")
        f.write(f"{content.strip()}\n\n")
