import asyncio

async def main():
    count = 0

    def make_counter():
        nonlocal count
        count = count + 1
        return count
    
    print("Starting")
    await asyncio.sleep(0.5)

    try:
        with open("temp.txt", "w") as f:
            while count < 3:
                f.write(f"{make_counter()}\n")
        
    except OSError as e:
        print("File error:", e)

asyncio.run(main())

print("Done")