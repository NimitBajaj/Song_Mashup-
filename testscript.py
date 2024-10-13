from youtubesearchpython import VideosSearch

def test_search(singer_name, num_videos=5):
    videos_search = VideosSearch(singer_name, limit=num_videos)
    results = videos_search.next()

    if isinstance(results, dict) and 'result' in results:
        if results['result']:
            print(f"Videos found for '{singer_name}':")
            for video in results['result']:
                print(f"Title: {video['title']}, Link: {video['link']}")
        else:
            print(f"No videos found for '{singer_name}'.")
    else:
        print("Unexpected result format:", results)

if __name__ == "__main__":
    singer_name = input("Enter the singer's name: ")
    test_search(singer_name)
