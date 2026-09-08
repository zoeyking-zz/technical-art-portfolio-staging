#pragma once

#include <GL/glew.h>
#include "glm/glm.hpp"
#include "glm/gtc/matrix_transform.hpp"

enum Camera_Movement {
	FORWARD,
	BACKWARD,
	LEFT,
	RIGHT,
	UP,
	DOWN
};

const float PICTH = 0.0f;
const float YAW = -90.0f;
const float SPEED = 2.5f;
const float SENSITIVITY = 0.1f;
const float ZOOM = 45.0f;

using namespace glm;
using namespace std;

class Camera
{
public:

	vec3 Position, Front, Up, WorldUp, Right;
	float Pitch, Yaw;
	float MovementSpeed, MouseSensitivity, Zoom;

	Camera(vec3 position = vec3(0.0f), vec3 up = vec3(0.0f, 1.0, 0.0f), float yaw = YAW, float pitch = PICTH)
		:Front(vec3(0.0f, 0.0f, -1.0f)), MovementSpeed(SPEED), MouseSensitivity(SENSITIVITY), Zoom(ZOOM)
	{
		this->Position = position;
		this->WorldUp = up;
		this->Pitch = pitch;
		this->Yaw = yaw;
		updataCameraVectors();
	}
	~Camera();

	mat4 GetViewMatrix();
	void ProcessMouseMovement(float xOffset, float yOffset) {

		xOffset *= this->MouseSensitivity;
		yOffset *= this->MouseSensitivity;

		this->Yaw += xOffset;
		this->Pitch += yOffset;

		if (this->Pitch >= 89.0f)
			this->Pitch = 89.0f;
		if (this->Pitch <= -89.0f)
			this->Pitch = -89.0f;

		updataCameraVectors();
		
	}
	void ProcessKeyboard(Camera_Movement dir, float deltaTime) {
		const float velocity = this->MovementSpeed*deltaTime;
		switch (dir)
		{
		case FORWARD:
			this->Position += this->Front*velocity;
			break;
		case BACKWARD:
			this->Position -= this->Front*velocity;
			break;
		case LEFT:
			this->Position -= this->Right*velocity;
			break;
		case RIGHT:
			this->Position += this->Right*velocity;
			break;
		case UP:
			this->Position += this->Up*velocity;
			break;
		case DOWN:
			this->Position -= this->Up*velocity;
			break;
		default:
			break;
		}

	}
	void ProcessMouseScroll(float yOffest) {
		this->Zoom -= float(yOffest);
		if (Zoom >= 45.0f)
			Zoom = 45.0f;
		if (Zoom <= 20.0f)
			Zoom = 20.0f;
	}

private:
	void updataCameraVectors() {
		glm::vec3 dir;
		dir.x = std::cos(glm::radians(this->Yaw))*std::cos(glm::radians(this->Pitch));
		dir.y = std::sin(glm::radians(this->Pitch));
		dir.x = std::sin(glm::radians(this->Yaw))*std::cos(glm::radians(this->Pitch));
		this->Front = glm::normalize(dir);

		this->Right = normalize(cross(this->Front, this->WorldUp));
		this->Up = normalize(cross(this->Right, this->Front));
	}
};



Camera::~Camera()
{
}


mat4 Camera::GetViewMatrix() {
	return lookAt(this->Position, this->Position*this->Front, this->Up);
}


