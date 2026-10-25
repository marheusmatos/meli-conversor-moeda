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
                withCredentials([file(credentialsId: 'meli-env', variable: 'ENV_FILE')]) {
                    sh '''
                        set -e
                        docker rm -f "$CONTAINER_NAME" || true

                        RUN="docker run -d --restart unless-stopped --env-file $ENV_FILE --add-host host.docker.internal:host-gateway -v meli-dev-data:/app/data --name $CONTAINER_NAME"

                        case "${BRANCH_NAME:-$GIT_BRANCH}" in
                            *develop) RUN="$RUN -e RATE_LIMIT__HABILITADO=false" ;;
                        esac

                        $RUN -p 127.0.0.1:$HOST_PORT:$CONTAINER_PORT -e API__ROOT_PATH=/meli/api "$IMAGE_NAME"
                    '''
                }
            }
        }
    }

    post {
        failure { echo 'Deploy falhou' }
        success { echo 'Deploy concluído com sucesso.' }
    }
}
