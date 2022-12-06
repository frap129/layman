from . import layman

def main():
    """Application entry point."""
   # Start layman
    daemon = layman.Layman()
    daemon.init()

if __name__ == '__main__':
    main()
