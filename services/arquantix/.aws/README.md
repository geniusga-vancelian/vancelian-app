# Configuration ECS Task Definition

Ce fichier contient la task definition pour le déploiement ECS du service Arquantix Coming Soon.

## Configuration requise

Avant d'utiliser cette task definition, vous devez renseigner les valeurs suivantes :

### 1. `executionRoleArn`

**Rôle IAM pour l'exécution de la tâche ECS** (permissions pour ECR, CloudWatch Logs, etc.)

**Où le trouver dans AWS :**
1. Ouvrez la console IAM : https://console.aws.amazon.com/iam/
2. Allez dans **Roles**
3. Recherchez un rôle contenant `ecsTaskExecutionRole` ou `ecs-execution-role`
4. Si aucun rôle n'existe, créez-en un avec la politique `AmazonECSTaskExecutionRolePolicy`
5. Copiez l'ARN complet (format : `arn:aws:iam::411714852748:role/nom-du-role`)

**Exemple :** `arn:aws:iam::411714852748:role/ecsTaskExecutionRole`

### 2. `taskRoleArn`

**Rôle IAM pour l'application elle-même** (permissions nécessaires à l'application en runtime)

**Où le trouver dans AWS :**
1. Ouvrez la console IAM : https://console.aws.amazon.com/iam/
2. Allez dans **Roles**
3. Recherchez un rôle existant pour votre service ECS
4. Si aucun rôle n'existe, créez-en un avec les permissions minimales nécessaires
5. Copiez l'ARN complet (format : `arn:aws:iam::411714852748:role/nom-du-role`)

**Note :** Si votre application n'a pas besoin de permissions AWS spécifiques, vous pouvez utiliser le même rôle que `executionRoleArn` ou créer un rôle vide.

**Exemple :** `arn:aws:iam::411714852748:role/ecsTaskRole`

## Comment obtenir les ARNs depuis une task definition existante

Si le service ECS existe déjà, vous pouvez récupérer les ARNs de la task definition actuelle :

```bash
aws ecs describe-services \
  --cluster arquantix-cluster \
  --services arquantix-coming-soon \
  --region me-central-1 \
  --query "services[0].taskDefinition" \
  --output text

aws ecs describe-task-definition \
  --task-definition <TASK_DEFINITION_ARN> \
  --region me-central-1 \
  --query "taskDefinition.{executionRoleArn:executionRoleArn,taskRoleArn:taskRoleArn}" \
  --output json
```

## Mise à jour

Après avoir renseigné les ARNs, remplacez `TO_BE_SET` par les valeurs réelles dans `task-definition.json`.








