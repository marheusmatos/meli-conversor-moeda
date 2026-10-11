pipeline {
    agent any

    environment {
        IMAGE_NAME     = 'meli'
        CONTAINER_NAME = 'meli'
        HOST_PORT      = '5500'
        CONTAINER_PORT = '8000'
        BASE_PATH      = '/meli'
    }

    stages {
        stage('Build') {
            steps {
                sh 'docker build -t $IMAGE_NAME .'
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    set -e

                    # Remove o container anterior, se existir
                    docker stop "$CONTAINER_NAME" || true
                    docker rm "$CONTAINER_NAME" || true

                    # Sobe o novo container
                    docker run -d \
                        -p 127.0.0.1:$HOST_PORT:$CONTAINER_PORT \
                        -e BASE_PATH="$BASE_PATH" \
                        --name "$CONTAINER_NAME" \
                        --restart unless-stopped \
                        "$IMAGE_NAME"
                '''
            }
        }
    }

    post {
        failure {
            echo 'Deploy falhou'
        }

        success {
            echo 'Deploy concluído com sucesso.'
        }
    }
}
