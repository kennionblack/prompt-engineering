#!/bin/bash

case "$1" in
    "start")
        docker-compose up -d
        sleep 10
        echo "MySQL container is ready!"
        ;;
    "stop")
        docker-compose down
        ;;
    "restart")
        docker-compose down
        docker-compose up -d
        sleep 10
        echo "MySQL container is ready!"
        ;;
    "reset")
        docker-compose down -v
        docker-compose up -d
        sleep 10
        echo "MySQL container reset!"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|reset}"
        echo "  start   - Start the MySQL container"
        echo "  stop    - Stop the MySQL container"
        echo "  restart - Restart the MySQL container"
        echo "  reset   - Reset database (removes all data)"
        exit 1
        ;;
esac