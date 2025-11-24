import asyncio
import uuid
import time

from temporalio.client import Client
from workflow import SupportTicketSystem
from models import Ticket

async def main():
    tickets = [
        Ticket("TEMP-001", "Alice Smith", "Can't login to account", "low"),
        Ticket("TEMP-002", "Bob Jones", "Payment processing stuck", "medium"),
        Ticket("TEMP-003", "Carol Williams", "Database corruption detected!", "high"),
        Ticket("TEMP-004", "Dave Brown", "API rate limits hit", "medium"),
        Ticket("TEMP-005", "Eve Davis", "SECURITY BREACH - immediate action needed", "high"),
        Ticket("TEMP-006", "Frank Miller", "Out of ideas", "low"),
        Ticket("TEMP-007", "Spongebob Squarepants", "Job stinks", "high"),
        Ticket("TEMP-008", "Patrick Star", "Adulting is hard", "low"),
        Ticket("TEMP-009", "Mr Krab", "Calculator broke", "low"),
        Ticket("TEMP-010", "Kevin Flynn", "Pet project went rogue", "high"),
        Ticket("TEMP-011", "Edward Dillinger", "Email notifications not working", "low"),
        Ticket("TEMP-012", "Quorra", "Matrix syndrome", "low"),
        Ticket("TEMP-013", "Wendy Carlos", "Ahead of her time", "high"),
        Ticket("TEMP-014", "Trent Reznor", "Excessive talent", "medium"),
        Ticket("TEMP-015", "Atticus Ross", "Misunderstood in his time", "low"),
        Ticket("TEMP-016", "Jordan Holmes", "Can't stop screaming", "low"),
        Ticket("TEMP-017", "Dan Friesen", "The mysterious professor won't disclose identity", "medium"),
        Ticket("TEMP-018", "Robert Evans", "There are bad people out there", "high"),
        Ticket("TEMP-019", "Jamie Loftus", "Hot dog is a sandwich and someone disagrees", "medium"),
        Ticket("TEMP-020", "Adam Driver", "Still too emo", "low"),
        Ticket("TEMP-021", "Max Rocketansky", "People can't get enough Type O", "high"),
        Ticket("TEMP-022", "Imperator Furiosa", "Boss too demanding", "medium"),
        Ticket("TEMP-023", "Wow Platinum", "It's right there in the name", "low"),
        Ticket("TEMP-024", "Vito Corleone", "Oranges aren't right", "high"),
        Ticket("TEMP-025", "Vincent Vega", "Incorrect shoe type for twist contest", "low"),
        Ticket("TEMP-026", "Mia Wallace", "Director won't give me socks", "medium"),
        Ticket("TEMP-027", "Waylon Smithers", "Boss too demanding", "high"),
        Ticket("TEMP-028", "Montgomery Burns", "Employees lazy and ungrateful", "low"),
        Ticket("TEMP-029", "Michael Albertson", "Nobody knows my name", "medium"),
        Ticket("TEMP-030", "Maggie Simpson", "I have a lot to say", "low"),
        Ticket("TEMP-031", "Bob Johnson", "Keep forgetting my own catchphrase", "medium"),
        Ticket("TEMP-032", "Carol Davis", "Geena keeps stealing my thunder", "high"),
        Ticket("TEMP-033", "David Wilson", "Tennis racket won't stop talking to me", "low"),
        Ticket("TEMP-034", "Eva Martinez", "Wall-E left me on spaceship again", "high"),
        Ticket("TEMP-035", "Frank Brown", "Charlie won't come out of his shell", "medium"),
        Ticket("TEMP-036", "Grace Lee", "Yoga students more flexible than me", "low"),
        Ticket("TEMP-037", "Henry Taylor", "Spidey sense tingling for wrong reasons", "high"),
        Ticket("TEMP-038", "Iris Chen", "Katniss shooting arrows at my fruit", "medium"),
        Ticket("TEMP-039", "Jack Robinson", "Rose won't share the door", "low"),
        Ticket("TEMP-040", "Kate Anderson", "Sandy keeps borrowing my lucky dress", "high"),
        Ticket("TEMP-041", "Liam O'Connor", "Wolves raised me wrong", "medium"),
        Ticket("TEMP-042", "Maya Patel", "Bees won't listen to my political advice", "low"),
        Ticket("TEMP-043", "Noah Garcia", "Animals keep showing up two by two", "high"),
        Ticket("TEMP-044", "Olivia Kim", "Fitz won't answer my calls", "medium"),
        Ticket("TEMP-045", "Paul Stevens", "Ant-Man suit shrunk my ego", "low"),
        Ticket("TEMP-046", "Quinn Murphy", "Harley won't stop asking about puddin", "high"),
        Ticket("TEMP-047", "Rachel Green", "Ross keeps saying we were on a break", "medium"),
        Ticket("TEMP-048", "Sam Thompson", "Gollum won't give back my ring", "low"),
        Ticket("TEMP-049", "Tina Rodriguez", "Puss in Boots stole my spotlight", "high"),
        Ticket("TEMP-050", "Whitney Houston", "Bodyguard taking job too seriously", "medium"),
        Ticket("TEMP-051", "Victoria Chang", "David won't stop asking about fashion", "low"),
        Ticket("TEMP-052", "William Jones", "Luke keeps asking about father issues", "high"),
        Ticket("TEMP-053", "Zoe Parker", "Can't decide between red pill or blue pill", "medium"),
        Ticket("TEMP-054", "Adam Miller", "Frankenstein's monster wants child support", "low"),
        Ticket("TEMP-055", "Beth Cooper", "Bradley won't stop being so attractive", "high"),
        Ticket("TEMP-056", "Chris Evans", "Shield keeps coming back like a boomerang", "medium"),
        Ticket("TEMP-057", "Diana Prince", "Lasso of truth revealing too much", "low"),
        Ticket("TEMP-058", "Eddie Brock", "Venom wants separate Netflix account", "high"),
        Ticket("TEMP-059", "Fiona Apple", "Johnny Cash walked the line through my garden", "medium"),
        Ticket("TEMP-060", "George Lucas", "Jar Jar won't stop asking for sequel roles", "low"),
        Ticket("TEMP-061", "Helen Troy", "Paris won't stop leaving wooden horses", "high"),
        Ticket("TEMP-062", "Ian Fleming", "James keeps breaking my spy gadgets", "medium"),
        Ticket("TEMP-063", "Jane Porter", "Tarzan swinging from wrong vines", "low"),
        Ticket("TEMP-064", "Kevin Hart", "Comedy club microphone too tall", "high"),
        Ticket("TEMP-065", "Luna Lovegood", "Nargles hiding my important documents", "medium"),
        Ticket("TEMP-066", "Mike Tyson", "Face tattoo removal failed", "low"),
        Ticket("TEMP-067", "Nina Simone", "Piano keys playing themselves at 3am", "high"),
        Ticket("TEMP-068", "Oscar Wilde", "Wit too sharp for Victorian sensibilities", "medium"),
        Ticket("TEMP-069", "Penny Lane", "Beatles won't get back together", "low"),
        Ticket("TEMP-070", "Quincy Adams", "John keeps stealing my presidential thunder", "high"),
        Ticket("TEMP-071", "Ruby Rose", "Orange is the new black but I prefer red", "medium"),
        Ticket("TEMP-072", "Steve Jobs", "Think different became think too different", "low"),
        Ticket("TEMP-073", "Tara Reid", "Sharknado franchise getting out of hand", "high"),
        Ticket("TEMP-074", "Uma Thurman", "Honzo sword keeps setting off metal detectors", "medium"),
        Ticket("TEMP-075", "Victor Hugo", "Hunchback keeps ringing bells at dawn", "low"),
        Ticket("TEMP-076", "Wendy Williams", "How you doin' getting repetitive responses", "high"),
        Ticket("TEMP-077", "Xavier Woods", "Professor X reading my mind during poker", "medium"),
        Ticket("TEMP-078", "Yara Shahidi", "Grown-ish cast keeps asking for life advice", "low"),
        Ticket("TEMP-079", "Zack Morris", "Time out power only works in high school", "high"),
        Ticket("TEMP-080", "Anna Kendrick", "Pitch Perfect harmonies stuck in my head", "medium"),
        Ticket("TEMP-081", "Blake Shelton", "Gwen keeps changing my country playlist", "low"),
        Ticket("TEMP-082", "Chloe Bennett", "SHIELD database password too complicated", "high"),
        Ticket("TEMP-083", "Derek Hale", "Full moon schedule conflicts with social life", "medium"),
        Ticket("TEMP-084", "Emma Stone", "La La Land critics still arguing about ending", "low"),
        Ticket("TEMP-085", "Felix Kjellberg", "Pewds fan mail blocking my mailbox", "high"),
        Ticket("TEMP-086", "Gal Gadot", "Wonder Woman costume uncomfortable for grocery shopping", "medium"),
        Ticket("TEMP-087", "Hunter Hayes", "Guitar strings keep breaking during performances", "low"),
        Ticket("TEMP-088", "Isla Fisher", "Wedding Crashers keep showing up uninvited", "high"),
        Ticket("TEMP-089", "James Bond", "Martini shaker license expired", "medium"),
        Ticket("TEMP-090", "Katy Perry", "Left Shark won't return my calls", "low"),
        Ticket("TEMP-091", "Leo DiCaprio", "Oscar keeps asking to be polished", "high"),
        Ticket("TEMP-092", "Mila Kunis", "Ashton pranking me through work computer", "medium"),
        Ticket("TEMP-093", "Neil Armstrong", "Moon rocks in garage attracting tourists", "low"),
        Ticket("TEMP-094", "Oprah Winfrey", "Everyone expects free cars at my parties", "high"),
        Ticket("TEMP-095", "Pedro Pascal", "Mandalorian helmet hair too hard to fix", "medium"),
        Ticket("TEMP-096", "Queen Latifah", "Royal duties conflicting with hip-hop career", "low"),
        Ticket("TEMP-097", "Ryan Reynolds", "Deadpool breaking fourth wall in real life", "high"),
        Ticket("TEMP-098", "Sandra Bullock", "Speed bus won't slow down in school zones", "medium"),
        Ticket("TEMP-099", "Tom Hanks", "Wilson volleyball demanding speaking role", "low"),
        Ticket("TEMP-100", "Viola Davis", "How to Get Away with Murder fans asking for legal advice", "high"),
    ]

    client = await Client.connect("localhost:7233")

    handles = []
    for i, ticket in enumerate(tickets, 1):
        workflow_id = f"ticket-{ticket.priority}-{ticket.ticket_id}-{uuid.uuid4()}"
        handle = await client.start_workflow(
            SupportTicketSystem.run,
            ticket,
            id=workflow_id,
            task_queue="workflows",
        )
        handles.append((handle, ticket, time.time()))
        print(f"🚀 Started workflow {i}/{len(tickets)}: {ticket.ticket_id} ({ticket.priority.upper()})")


if __name__ == "__main__":
    asyncio.run(main())