pipeline {
    agent any

    environment {
        IMAGE_NAME     = 'meli-dev'
        CONTAINER_NAME = 'meli-dev'
        HOST_PORT      = '5500'
        CONTAINER_PORT = '8000'
    }

    stages {
        stage('Build') {
            steps {
                sh 'docker build -t $IMAGE_NAME .'
            }
        }

        stage('Deploy') {
            steps {
                withCredentials([
                    file(credentialsId: 'meli-env', variable: 'ENV_FILE')
                ]) {
                    sh '''
                        set -e

                        docker stop "$CONTAINER_NAME" || true
                        docker rm "$CONTAINER_NAME" || true

                        case "${BRANCH_NAME:-$GIT_BRANCH}" in
                            *develop) RATE_LIMIT_ENABLED=false ;;
                            *) RATE_LIMIT_ENABLED=true ;;
                        esac

                        docker run -d \
                            -p 127.0.0.1:$HOST_PORT:$CONTAINER_PORT \
                            --env-file "$ENV_FILE" \
                            -e RATE_LIMIT_ENABLED="$RATE_LIMIT_ENABLED" \
                            -e BASE_PATH=/meli/api \
                            --name "$CONTAINER_NAME" \
                            --restart unless-stopped \
                            "$IMAGE_NAME"
                    '''
                }
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
