#include <GL/glew.h>
#include <GLFW/glfw3.h>
#include <iostream>
#include "shader.h"
#include "camera.hpp"
#include "stb_image.h"
#include "glm/glm.hpp"
#include "glm/gtc/matrix_transform.hpp"
#include "glm/gtc/type_ptr.hpp"

#define SCR_WIDTH	1000
#define SCR_HEIGHT	800

/*Buffers*/
GLuint VBO, VAO, EBO;
GLuint lightCubeVBO, lightCubeVAO;

/*Matrices*/
glm::mat4 model;
glm::mat4 projection, view;

//vec3 lightPos = vec3(0.0f, 0.5f, 1.0f);

/*Vectors
glm::vec3 myPos;
glm::vec3 cameraPos = glm::vec3(0.0f, 0.0f, 3.0f);
glm::vec3 cameraFront = glm::vec3(0.0f, 0.0f, -1.0f);
glm::vec3 cameraUp = glm::vec3(0.0f, 1.0f, 0.0f);*/

/*Frames*/
float deltaTime = 0.0f;
float lastFrame = 0.0f;

/*Camera Attributes*/
/*
float pitch = 0.0f;
float yaw = -90.0f;
float zoom = 45.0f;*/
Camera camera(vec3(0.0f, 0.0f, 3.0f));
float lastX = float(SCR_WIDTH) / 2.0f;
float lastY = float(SCR_HEIGHT) / 2.0f;
bool isFirstMouse = true;



float vertices[] = {
	/*Left Position*/	/*Color*/			/*TexCoords*/	/*Normals*/
	-0.5f,-0.5f,-0.5f,	1.0f,0.0f,0.0f,		0.0f,0.0f,		-1.0f, 0.0f, 0.0f,
	-0.5f, 0.5f,-0.5f,	0.0f,1.0f,0.0f,		1.0f,0.0f,		-1.0f, 0.0f, 0.0f,
	-0.5f, 0.5f, 0.5f,	0.0f,0.0f,1.0f,		1.0f,1.0f,		-1.0f, 0.0f, 0.0f,
	-0.5f, 0.5f, 0.5f,	0.0f,0.0f,1.0f,		1.0f,1.0f,		-1.0f, 0.0f, 0.0f,
	-0.5f,-0.5f, 0.5f,	1.0f,0.0f,1.0f,		0.0f,1.0f,		-1.0f, 0.0f, 0.0f,
	-0.5f,-0.5f,-0.5f,	1.0f,0.0f,0.0f,		0.0f,0.0f,		-1.0f, 0.0f, 0.0f,

	/*Backward Position*/	/*Color*/		/*TexCoords*/
	-0.5f,-0.5f,-0.5f,	1.0f,0.0f,0.0f,		0.0f,0.0f,		 0.0f,-1.0f, 0.0f,
	 0.5f,-0.5f,-0.5f,	0.0f,1.0f,0.0f,		1.0f,0.0f,		 0.0f,-1.0f, 0.0f,
	 0.5f,-0.5f, 0.5f,	0.0f,0.0f,1.0f,		1.0f,1.0f,		 0.0f,-1.0f, 0.0f,
	 0.5f,-0.5f, 0.5f,	0.0f,0.0f,1.0f,		1.0f,1.0f,		 0.0f,-1.0f, 0.0f,
	-0.5f,-0.5f, 0.5f,	1.0f,0.0f,1.0f,		0.0f,1.0f,		 0.0f,-1.0f, 0.0f,
	-0.5f,-0.5f,-0.5f,	1.0f,0.0f,0.0f,		0.0f,0.0f,		 0.0f,-1.0f, 0.0f,

	/*Bottom Position*/	/*Color*/			/*TexCoords*/
	-0.5f,-0.5f,-0.5f,	1.0f,0.0f,0.0f,		0.0f,0.0f,		 0.0f, 0.0f,-1.0f,
	 0.5f,-0.5f,-0.5f,	0.0f,1.0f,0.0f,		1.0f,0.0f,		 0.0f, 0.0f,-1.0f,
	 0.5f, 0.5f,-0.5f,	0.0f,0.0f,1.0f,		1.0f,1.0f,		 0.0f, 0.0f,-1.0f,
	 0.5f, 0.5f,-0.5f,	0.0f,0.0f,1.0f,		1.0f,1.0f,		 0.0f, 0.0f,-1.0f,
	-0.5f, 0.5f,-0.5f,	1.0f,0.0f,1.0f,		0.0f,1.0f,		 0.0f, 0.0f,-1.0f,
	-0.5f,-0.5f,-0.5f,	1.0f,0.0f,0.0f,		0.0f,0.0f,		 0.0f, 0.0f,-1.0f,

	/*Top Position*/	/*Color*/			/*TexCoords*/
	-0.5f,-0.5f,0.5f,	1.0f,0.0f,0.0f,		0.0f,0.0f,		 0.0f, 0.0f, 1.0f,
	 0.5f,-0.5f,0.5f,	0.0f,1.0f,0.0f,		1.0f,0.0f,		 0.0f, 0.0f, 1.0f,
	 0.5f, 0.5f,0.5f,	0.0f,0.0f,1.0f,		1.0f,1.0f,		 0.0f, 0.0f, 1.0f,
	 0.5f, 0.5f,0.5f,	0.0f,0.0f,1.0f,		1.0f,1.0f,		 0.0f, 0.0f, 1.0f,
	-0.5f, 0.5f,0.5f,	1.0f,0.0f,1.0f,		0.0f,1.0f,		 0.0f, 0.0f, 1.0f,
	-0.5f,-0.5f,0.5f,	1.0f,0.0f,0.0f,		0.0f,0.0f,		 0.0f, 0.0f, 1.0f,

	/*Front Position*/	/*Color*/			/*TexCoords*/
	-0.5f, 0.5f,-0.5f,	1.0f,0.0f,0.0f,		0.0f,0.0f,		 0.0f, 1.0f, 0.0f,
	 0.5f, 0.5f,-0.5f,	0.0f,1.0f,0.0f,		1.0f,0.0f,		 0.0f, 1.0f, 0.0f,
	 0.5f, 0.5f, 0.5f,	0.0f,0.0f,1.0f,		1.0f,1.0f,		 0.0f, 1.0f, 0.0f,
	 0.5f, 0.5f, 0.5f,	0.0f,0.0f,1.0f,		1.0f,1.0f,		 0.0f, 1.0f, 0.0f,
	-0.5f, 0.5f, 0.5f,	1.0f,0.0f,1.0f,		0.0f,1.0f,		 0.0f, 1.0f, 0.0f,
	-0.5f, 0.5f,-0.5f,	1.0f,0.0f,0.0f,		0.0f,0.0f,		 0.0f, 1.0f, 0.0f,
															 
	/*Right Position*/	/*Color*/			/*TexCoords*/	 
	 0.5f,-0.5f,-0.5f,	1.0f,0.0f,0.0f,		0.0f,0.0f,		 1.0f, 0.0f, 0.0f,
	 0.5f, 0.5f,-0.5f,	0.0f,1.0f,0.0f,		1.0f,0.0f,		 1.0f, 0.0f, 0.0f,
	 0.5f, 0.5f, 0.5f,	0.0f,0.0f,1.0f,		1.0f,1.0f,		 1.0f, 0.0f, 0.0f,
	 0.5f, 0.5f, 0.5f,	0.0f,0.0f,1.0f,		1.0f,1.0f,		 1.0f, 0.0f, 0.0f,
	 0.5f,-0.5f, 0.5f,	1.0f,0.0f,1.0f,		0.0f,1.0f,		 1.0f, 0.0f, 0.0f,
	 0.5f,-0.5f,-0.5f,	1.0f,0.0f,0.0f,		0.0f,0.0f,		 1.0f, 0.0f, 0.0f,
};
vec3 cube_position[] = {
	vec3( 0.0f, 0.0f,  0.0f),
	vec3( 2.0f, 5.0f,-15.0f),
	vec3(-1.5f,-2.0f,  2.0f),
	vec3(-4.0f,-2.0f,-10.0f),
	vec3( 3.0f,-1.0f, -4.0f),
	vec3(-2.0f, 3.0f, -8.0f),
	vec3( 2.0f,-2.0f,-10.0f),
	vec3( 2.0f, 2.0f,  5.0f),
};
vec3 lightCube_position[] = {
	vec3( 0.0f, 0.0f, 0.0f),
	vec3(-6.0f, 0.0f, 0.0f),
	vec3( 6.0f,-6.0f, 0.0f),
	vec3(-6.0f, 6.0f,-6.0f),
};

/*
const char* vs =
"#version 330 core\n"
"layout(location = 0 )in vec3 aPos;"
"layout(location = 1 )in vec3 aColor;"
"out vec3 ourColor;"
"void main()"
"{"
"	ourColor = aColor;"
"	gl_Position = vec4(aPos,1.0f);"
"}";

const char* fs =
"#version 330 core\n"
"out vec4 FragColor;"
"in vec3 ourColor;"
"uniform float xColor;"
"void main()"
"{"
"	FragColor=vec4(xColor*ourColor.x,ourColor.y,ourColor.z,1.0f);"
"}";*/

void framebuffer_size_callback(GLFWwindow* window, int width, int height) {
	glViewport(0, 0, width, height);
}
void userInput(GLFWwindow* window) {
	const float camera_speed = 2.5f*deltaTime;
	
	if (glfwGetKey(window, GLFW_KEY_E) == GLFW_TRUE)
		camera.ProcessKeyboard(FORWARD, deltaTime);
	else if (glfwGetKey(window, GLFW_KEY_Q) == GLFW_TRUE)
		camera.ProcessKeyboard(BACKWARD, deltaTime);
	else if (glfwGetKey(window, GLFW_KEY_D) == GLFW_TRUE)
		camera.ProcessKeyboard(RIGHT, deltaTime);
	else if (glfwGetKey(window, GLFW_KEY_A) == GLFW_TRUE)
		camera.ProcessKeyboard(LEFT, deltaTime);
	else if (glfwGetKey(window, GLFW_KEY_W) == GLFW_TRUE)
		camera.ProcessKeyboard(UP, deltaTime);
	else if (glfwGetKey(window, GLFW_KEY_S) == GLFW_TRUE)
		camera.ProcessKeyboard(DOWN, deltaTime);

	if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
	{
		glfwSetWindowShouldClose(window, GLFW_TRUE);
		std::cout << "SetWindowShouldClose.\n";
	}
}
void mouse_cursor_position(GLFWwindow* window, double xpos, double ypos) {
	std::cout << "Mouse's position:" << xpos << "	" << ypos << std::endl;
	if (isFirstMouse) {
		lastX = xpos;
		lastY = ypos;
		isFirstMouse = false;

	}

	float xOffset = xpos - lastX;
	float yOffset = lastY - ypos;
	lastX = xpos;
	lastY = ypos;

	camera.ProcessMouseMovement(xOffset, yOffset);
}
void mouse_scroll_position(GLFWwindow* window, double xoffest, double yoffest) {
	std::cout << "xOffest:" << xoffest << "	yOffest" << yoffest << "\n";
	camera.ProcessMouseScroll(yoffest);
}
GLuint load_texture(const char*texture_path) {
	GLuint texture;
	glGenTextures(1, &texture);
	glBindTexture(GL_TEXTURE_2D, texture);

	/*Filters*/
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_NEAREST);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR_MIPMAP_NEAREST);

	int width, height, nrChannels;
	unsigned char* data = stbi_load(texture_path, &width, &height, &nrChannels, 0);
	if (data) {
		GLenum format;
		if (nrChannels == 1)
			format = GL_RED;
		else if (nrChannels == 3)
			format = GL_RGB;
		else if (nrChannels == 4)
			format = GL_RGBA;

		glTexImage2D(GL_TEXTURE_2D, 0, format, width, height, 0, format, GL_UNSIGNED_BYTE, data);
		glGenerateMipmap(GL_TEXTURE_2D);
		std::cout << "Find texture_path:" << texture_path << "\n";
	}
	else
	{
		std::cout << "Failed to load texture.\n";
	}

	stbi_image_free(data);
	return texture;
}

void BindBuffer() {
	
	glGenVertexArrays(1, &VAO);
	glGenBuffers(1, &VBO);
	glBindVertexArray(VAO);
	glBindBuffer(GL_ARRAY_BUFFER, VBO);
	glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), &vertices, GL_STATIC_DRAW);

	glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 11 * sizeof(float), (void*)0);
	glEnableVertexAttribArray(0);					
	glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 11 * sizeof(float), (void*)(3 * sizeof(float)));
	glEnableVertexAttribArray(1);					
	glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 11 * sizeof(float), (void*)(6 * sizeof(float)));
	glEnableVertexAttribArray(2);
	glVertexAttribPointer(3, 3, GL_FLOAT, GL_FALSE, 11 * sizeof(float), (void*)(8 * sizeof(float)));
	glEnableVertexAttribArray(3);
	
}
void BindLightBuffers() {

	glGenVertexArrays(1, &lightCubeVAO);
	glGenBuffers(1, &lightCubeVBO);
	glBindVertexArray(lightCubeVAO);
	glBindBuffer(GL_ARRAY_BUFFER, lightCubeVBO);
	glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), &vertices, GL_STATIC_DRAW);

	glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 11 * sizeof(float), (void*)0);
	glEnableVertexAttribArray(0);

}

int main(void)
{
	GLFWwindow* window;

	/* Initialize the library */
	glfwInit();

	/*Initializa Version 3.3*/
	glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
	glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
	glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

	/* Create a windowed mode window and its OpenGL context */
	window = glfwCreateWindow(SCR_WIDTH, SCR_HEIGHT, "OpenGL3.3", NULL, NULL);
	if (!window)
	{
		glfwTerminate();
		return -1;
	}

	/* Make the window's context current */
	glfwMakeContextCurrent(window);
	glfwSetFramebufferSizeCallback(window, framebuffer_size_callback);
	glfwSetCursorPosCallback(window, mouse_cursor_position);
	glfwSetScrollCallback(window, mouse_scroll_position);
	//glfwSetInputMode(window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);

	/*Check Glew*/
	if (glewInit() != GLEW_OK) {
		std::cout << "Failed too initializa Glew" << std::endl;
		glfwTerminate();
	}

	/*Option*/
	glEnable(GL_DEPTH_TEST);


	/*Buffers*/
	BindBuffer();
	BindLightBuffers();

	/*Texture*/
	stbi_set_flip_vertically_on_load(true);
	GLuint WaterTexture = load_texture("water.jpg");
	GLuint GrassTexture = load_texture("grass.jpg");
	GLuint BottleTexture = load_texture("bottle.png");
	GLuint FrameTexture = load_texture("frame.png");
	Shader myShader("vertexShader.glsl", "fragmentShader.glsl"); 
	myShader.use();
	myShader.setInt("mT1.diffuse", 0);
	myShader.setInt("mT1.specular", 1);

	Shader lightCubeShader("lightCube.vert", "lightCube.frag");
	

	/* Loop until the user closes the window */
	while (!glfwWindowShouldClose(window)) 
	{
		/*Updata*/
		userInput(window);
		float time = glfwGetTime();
		deltaTime = time - lastFrame;
		lastFrame = time;
		float radius = 3.0f;
		float camX = std::sin(time)*radius;
		float camZ = std::cos(time)*radius;
		static float shininess = 32.0f;
		/*
		float xValue = std::cos(time) / 2.0f + 0.5f;
		float Angle = std::cos(time) * 2;
		myShader.setFloat("xColor", xValue);
		model = glm::mat4(1.0f);
		//model = glm::scale(model, glm::vec3(0.5f, 0.5f, 0.5f));
		model = glm::translate(model, glm::vec3(myPos));
		//model = glm::rotate(model, glm::radians(46.0f)*Angle, glm::vec3(0.0f, 0.0f, 1.0f));
		myShader.setMat4("model", model);*/

		/*set"myShader"*/
		myShader.use();
		myShader.setVec3("viewPos", camera.Position);
		//if you don't have "struct Material"
		/*
		myShader.setVec3("objectColor", 1.0f, 0.3f, 0.6f);
		myShader.setFloat("shininess", shininess);
		*/
		//myShader.setVec3("mT1.ambient", 1.0f, 0.3f, 0.6f);
		//myShader.setVec3("mT1.diffuse", 1.0f, 0.3f, 0.6f);
		myShader.setVec3("mT1.specular", vec3(0.5f));
		myShader.setFloat("mT1.shininess", 64.0f);
		
		vec3 lightPos = vec3(camX, 0.0f, camZ);
		//if you don't have "struct Light"
		/*
		myShader.setVec3("lightColor", vec3(1.0f));
		myShader.setVec3("lightPos", lightPos);
		*/
		
		myShader.setVec3 ("lDir.direction", 0.0f, 0.0f,-10.0f);
		//myShader.setVec3("lDir.direction", lightPos);
		myShader.setVec3 ("lDir.ambient", vec3(0.05f));
		myShader.setVec3 ("lDir.diffuse", vec3(0.05f));
		myShader.setVec3 ("lDir.specular", vec3(0.05f));

		for (int i = 0;i < 4;i++) {
			if (i == 0)
				myShader.setVec3(("lPoint[" + to_string(i) + "].position").c_str(), lightPos);
			else
				myShader.setVec3 (("lPoint["+ to_string(i)+"].position" ).c_str(), lightCube_position[i]);
			myShader.setVec3 (("lPoint["+ to_string(i)+"].ambient"  ).c_str(), vec3(0.5f));
			myShader.setVec3 (("lPoint["+ to_string(i)+"].diffuse"  ).c_str(), vec3(0.4f));
			myShader.setVec3 (("lPoint["+ to_string(i)+"].specular" ).c_str(), vec3(0.9f));
			myShader.setFloat(("lPoint["+ to_string(i)+"].constant" ).c_str(), 1.0f);
			myShader.setFloat(("lPoint["+ to_string(i)+"].linear"   ).c_str(), 0.09f);
			myShader.setFloat(("lPoint["+ to_string(i)+"].quadratic").c_str(), 0.032f);
		}
								  

		projection = glm::perspective(glm::radians(camera.Zoom), float(SCR_WIDTH) / float(SCR_HEIGHT), 1.0f, 100.0f);
		myShader.setMat4("projection", projection);

		view = glm::mat4(1.0f);
		view = glm::translate(view, glm::vec3(0.0f, 0.0f,-8.0f));
		//view = glm::lookAt(cameraPos, cameraPos + cameraFront, cameraUp);
		view = camera.GetViewMatrix();
		myShader.setMat4("view", view);

		model = glm::mat4(1.0f);
		model = glm::rotate(model, glm::radians(-55.0f)*time, glm::vec3(1.0f));
		//model = glm::translate(model, glm::vec3(myPos));
		myShader.setMat4("model", model);

		/*set"lightCubeShader"*/
		

		/* Render here */
		glClearColor(1.0f, 0.8f, 0.8f, 1.0f);
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

		
		glActiveTexture(GL_TEXTURE0);
		glBindTexture(GL_TEXTURE_2D, GrassTexture);
		glActiveTexture(GL_TEXTURE1);
		glBindTexture(GL_TEXTURE_2D, FrameTexture);
		//myShader.use();
		for (int i = 0;i < 10;i++) {
			model = glm::mat4(1.0f);
			model = glm::translate(model, glm::vec3(cube_position[i]));
			myShader.setMat4("model", model);
			glBindVertexArray(VAO);
			glDrawArrays(GL_TRIANGLES, 0, 36);
		}
		
		lightCubeShader.use();
		lightCubeShader.setMat4("projection", projection);
		lightCubeShader.setMat4("view", view);

		for (int i = 0;i < 4;i++) {
			model = mat4(1.0f);
			if (i == 0)
				model = translate(model, lightPos);
			else
				model = translate(model, lightCube_position[i]);
			model = scale(model, vec3(0.3f));
			lightCubeShader.setMat4("model", model);
			glBindVertexArray(lightCubeVAO);
			glDrawArrays(GL_TRIANGLES, 0, 36);
		}
		

		/* Swap front and back buffers */
		glfwSwapBuffers(window);

		/* Poll for and process events */
		glfwPollEvents();

	}

	glfwDestroyWindow(window);
	glfwTerminate();
	return 0;
}

