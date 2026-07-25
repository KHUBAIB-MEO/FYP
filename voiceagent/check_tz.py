from voiceagent.core.calendar_agent import CalendarAgent
cal = CalendarAgent()
setting = cal.service.settings().get(setting="timezone").execute()
print("Your Google Calendar timezone is:", setting.get("value"))